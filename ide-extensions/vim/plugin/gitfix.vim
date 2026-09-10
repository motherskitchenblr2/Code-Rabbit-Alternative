" =============================================================================
" Git-Fix Vim Plugin
# =============================================================================
# Git-Fix Vim/Neovim Plugin
# Cyberpunk Code Review Engine integration for Vim/Neovim
# =============================================================================

if exists('g:loaded_gitfix')
  finish
endif
let g:loaded_gitfix = 1

" =============================================================================
# Configuration
# =============================================================================

" Default configuration
let g:gitfix_config = get(g:, 'gitfix_config', {
      \ 'api_url': 'http://localhost:5000',
      \ 'ws_url': 'ws://localhost:5000/ws',
      \ 'enabled': 1,
      \ 'auto_review': 1,
      \ 'severity_threshold': 'medium',
      \ 'show_inline_annotations': 1,
      \ 'show_status_bar': 1,
      \ 'realtime_updates': 1,
      \ 'languages': ['python', 'typescript', 'javascript', 'go', 'rust', 'java', 'cpp'],
      \ 'scan_dirty_files': 0,
      \ 'max_file_size': 1048576,
      \ 'exclude_patterns': [
      \   '**/node_modules/**',
      \   '**/.git/**',
      \   '**/dist/**',
      \   '**/build/**',
      \   '**/*.min.js',
      \   '**/vendor/**'
      \ ],
      \ 'scan_on_save': 1,
      \ 'scan_on_type': 0,
      \ 'scan_debounce_ms': 500,
      \ 'show_inline_fixes': 1,
      \ 'show_codelens': 1,
      \ 'enable_sounds': 0,
      \ 'theme': 'auto',
      \ 'accent_color': 'magenta',
      \ 'animation_enabled': 1,
    \ }

" Merge user config with defaults
function! s:merge_config() abort
  let g:gitfix_config = extend(deepcopy(g:gitfix_config_default), g:gitfix_config, 'force')
endfunction

let g:gitfix_config_default = g:gitfix_config
call s:merge_config()

" =============================================================================
# State
# =============================================================================

let s:findings = []
let s:diagnostics = {}
let s:ws = 0
let s:reconnect_attempts = 0
let s:max_reconnect_attempts = 5
let s:scan_timer = 0

" =============================================================================
# Utility Functions
# =============================================================================

function! s:log(msg) abort
  if has('nvim')
    call luaeval('vim.notify(_A[1], vim.log.levels.INFO)', [a:msg])
  else
    echom '[Git-Fix] ' . a:msg
  endif
endfunction

function! s:warn(msg) abort
  if has('nvim')
    call luaeval('vim.notify(_A[1], vim.log.levels.WARN)', [a:msg])
  else
    echohl WarningMsg
    echom '[Git-Fix] ' . a:msg
    echohl None
  endif
endfunction

function! s:error(msg) abort
  if has('nvim')
    call luaeval('vim.notify(_A[1], vim.log.levels.ERROR)', [a:msg])
  else
    echohl ErrorMsg
    echom '[Git-Fix] ' . a:msg
    echohl None
  endif
endfunction

function! s:notify(msg, level) abort
  if has('nvim')
    call luaeval('vim.notify(_A[1], _A[2])', [a:msg, a:level])
  else
    if a:level == 'error'
      call s:error(a:msg)
    elseif a:level == 'warn'
      call s:warn(a:msg)
    else
      call s:log(a:msg)
    endif
  endif
endfunction

function! s:get_config(key) abort
  return get(g:gitfix_config, a:key, '')
endfunction

function! s:should_scan() abort
  if !g:gitfix_config.enabled
    return 0
  endif
  
  let ft = &filetype
  if index(g:gitfix_config.languages, ft) == -1
    return 0
  endif
  
  if !g:gitfix_config.scan_dirty_files && &modified
    return 0
  endif
  
  let max_size = g:gitfix_config.max_file_size
  if line2byte(line('$') + 1) > g:gitfix_config.max_file_size
    return 0
  endif
  
  let fname = expand('%:p')
  for pattern in g:gitfix_config.exclude_patterns
    if fname =~# pattern
      return 0
    endif
  endfor
  
  return 1
endfunction

" =============================================================================
# API Client
# =============================================================================

let s:api_base_url = 'http://localhost:5000'
let s:ws_url = 'ws://localhost:5000/ws'

function! s:api_request(method, endpoint, data) abort
  let url = s:api_base_url . a:endpoint
  let headers = {
        \ 'Content-Type': 'application/json',
        \ 'User-Agent': 'Git-Fix-Vim/1.0'
      \ }
  
  if !empty($GITFIX_API_TOKEN)
    let headers['Authorization'] = 'Bearer ' . $GITFIX_API_TOKEN
  endif
  
  let cmd = 'curl -s -X ' . a:method . ' '
  let cmd .= '-H "Content-Type: application/json" '
  for [key, val] in items(headers)
    let cmd .= '-H "' . key . ': ' . val . '" '
  endfor
  if a:method != 'GET' && a:data != v:null
    let cmd .= '-d ' . shellescape(json_encode(a:data))
  endif
  let cmd .= ' ' . shellescape(s:api_base_url . a:endpoint)
  
  let output = system(cmd)
  if v:shell_error
    call s:error('API request failed: ' . output)
    return {}
  endif
  return json_decode(output)
endfunction

function! GitFixScanCode(code, language, filepath) abort
  let payload = {
        \ 'code': a:code,
        \ 'language': a:language,
        \ 'file_path': a:filepath,
      \ }
  return s:api_request('POST', '/api/v1/scan', payload)
endfunction

function! GitFixDismissFinding(finding_id) abort
  call s:api_request('DELETE', '/api/v1/findings/' . a:finding_id . '/dismiss', {})
endfunction

" =============================================================================
# WebSocket Connection
# =============================================================================

function! GitFixConnectWS() abort
  if s:ws != 0
    return
  endif
  
  if has('nvim')
    " Use nvim's built-in WebSocket
    lua << EOF
    local ws_url = vim.g.gitfix_config.ws_url or 'ws://localhost:5000/ws'
    local ws = vim.uv.new_tcp()
    ws:connect('127.0.0.1', 5000, function()
      ws:read_start(function(err, data)
        if err then
          vim.notify('WS Error: ' .. err, vim.log.levels.ERROR)
          return
        end
        if data then
          vim.schedule(function()
            local ok, msg = pcall(vim.json.decode, data)
            if ok and msg then
              if msg.type == 'findings' then
                vim.api.nvim_exec_autocmds('User', {pattern = 'GitFixFindingsUpdate', data = msg.findings})
              elseif msg.type == 'pipeline' then
                vim.api.nvim_exec_autocmds('User', {pattern = 'GitFixPipelineUpdate', data = msg.pipeline})
              end
            end
          end)
        end
      end)
    end)
    vim.g.gitfix_ws = ws
EOF
  else
    " Vim - use external WebSocket client
    call s:warn('WebSocket not fully supported in Vim. Use Neovim for real-time updates.')
  endif
endfunction

function! GitFixDisconnectWS() abort
  if has('nvim')
    lua << EOF
    if vim.g.gitfix_ws then
      vim.g.gitfix_ws:close()
      vim.g.gitfix_ws = nil
    end
EOF
  endif
endfunction

" =============================================================================
# Diagnostics
# =============================================================================

let s:ns_id = 0
if has('nvim')
  let s:ns_id = nvim_create_namespace('GitFix')
endif

function! GitFixUpdateDiagnostics(bufnr, findings) abort
  if !has('nvim')
    return
  endif
  
  if a:bufnr == 0
    let bufnr = bufnr('%')
  endif
  
  let diagnostics = []
  for finding in a:findings
    let line = get(finding, 'line_start', get(finding, 'line', 1)) - 1
    let end_line = get(finding, 'line_end', line + 1) - 1
    let severity = get(finding, 'severity', 'info')
    
    let diagnostic = {
          \ 'lnum': line,
          \ 'end_lnum': end_line,
          \ 'col': 0,
          \ 'end_col': 100,
          \ 'severity': s:map_severity(severity),
          \ 'message': get(finding, 'message', ''),
          \ 'source': 'Git-Fix',
          \ 'code': get(finding, 'category', ''),
          \ 'user_data': {
                \ 'finding_id': get(finding, 'id', ''),
                \ 'suggested_fix': get(finding, 'suggested_fix', ''),
              \ },
        \ }
    call add(diagnostics, diagnostic)
  endfor
  
  call nvim_buf_set_diagnostic(a:bufnr, s:ns_id, diagnostics)
endfunction

function! s:map_severity(severity) abort
  let map = {
        \ 'critical': 1,
        \ 'high': 1,
        \ 'medium': 2,
        \ 'low': 3,
        \ 'info': 4,
      \ }
  return get(map, a:severity, 4)
endfunction

function! GitFixClearDiagnostics(bufnr) abort
  if has('nvim') && a:bufnr > 0
    call nvim_buf_clear_namespace(a:bufnr, s:ns_id, 0, -1)
  endif
endfunction

" =============================================================================
# Commands
# =============================================================================

command! -nargs=0 GitFixScanFile call GitFixScanCurrentFile()
command! -nargs=0 GitFixScanWorkspace call GitFixScanWorkspace()
command! -nargs=0 GitFixOpenDashboard call GitFixOpenDashboard()
command! -nargs=0 GitFixShowFindings call GitFixShowFindings()
command! -nargs=* GitFixApplyFix call GitFixApplyFix(<f-args>)
command! -nargs=* GitFixDismissFinding call GitFixDismissFinding(<f-args>)
command! -nargs=0 GitFixConfigure call GitFixConfigure()
command! -nargs=0 GitFixViewReport call GitFixViewReport()
command! -nargs=0 GitFixToggleAutoReview call GitFixToggleAutoReview()
command! -nargs=0 GitFixStatus call GitFixStatus()
command! -nargs=0 GitFixConnect call GitFixConnectWS()
command! -nargs=0 GitFixDisconnect call GitFixDisconnectWS()

function! GitFixScanCurrentFile() abort
  if !s:should_scan()
    return
  endif
  
  let code = join(getline(1, '$'), "\n")
  let language = &filetype
  let filepath = expand('%:p')
  
  if empty(code)
    call s:notify('File is empty', 'info')
    return
  endif
  
  call s:notify('Scanning ' . expand('%:t') . '...', 'info')
  
  try
    let result = GitFixScanCode(join(getline(1, '$'), "\n"), &filetype, expand('%:p'))
    if has_key(result, 'findings')
      call GitFixUpdateDiagnostics(bufnr('%'), result.findings)
      call s:notify('Scan complete: ' . len(result.findings) . ' findings', 'info')
    endif
  catch
    call s:error('Scan failed: ' . v:exception)
  endtry
endfunction

function! GitFixScanWorkspace() abort
  let files = split(globpath('.', '**', 0, 1), '\n')
  let filtered = filter(copy(files), {idx, f -> 
        \ f !~# 'node_modules' && f !~# '\.git' && 
        \ f !~# '\.min\.js$' && f !~# '\.min\.css$' &&
        \ f !~# 'vendor' && f !~# 'dist' && f !~# 'build'
      \})
  
  if empty(filtered)
    call s:notify('No files to scan', 'info')
    return
  endif
  
  let total = len(filtered)
  let scanned = 0
  
  for file in filtered
    try
      let code = readfile(fnameescape(f), 'b')
      let ft = matchstr(f, '\.[^.]*$')[1:]  " get extension
      call GitFixScanCode(join(f, "\n"), ft, f)
      let scanned += 1
      echon "\rScanning: " . scanned . "/" . total . " files"
      redraw
    catch
      call s:warn("Failed to scan " . v:val . ": " . v:exception)
    endtry
  endfor
  
  echon "\r"
  call s:notify('Workspace scan complete: ' . scanned . ' files scanned', 'info')
endfunction

function! GitFixOpenDashboard() abort
  if has('nvim')
    lua << EOF
    vim.ui.open('http://localhost:5173')
EOF
  else
    silent execute '!open http://localhost:5173 2>/dev/null || xdg-open http://localhost:5173 2>/dev/null || start http://localhost:5173'
  endif
endfunction

function! GitFixShowFindings() abort
  " Open findings in quickfix or location list
  let findings = g:gitfix_findings
  if empty(findings)
    call s:notify('No findings available', 'info')
    return
  endif
  
  let qflist = []
  for finding in g:gitfix_findings
    call add(g:qflist, {
          \ 'filename': get(finding, 'file_path', ''),
          \ 'lnum': get(finding, 'line_start', 1),
          \ 'col': 1,
          \ 'text': get(finding, 'message', ''),
          \ 'type': get(finding, 'severity', 'I')[0:0],
          \ 'valid': 1,
        \ })
  endfor
  
  call setqflist({}, 'r', {'title': 'Git-Fix Findings', 'items': g:qflist})
  copen
endfunction

function! GitFixApplyFix(args) abort
  if a:0 == 0
    call s:error('Usage: GitFixApplyFix <finding_id>')
    return
  endif
  
  let finding_id = a:1
  let findings = g:gitfix_findings
  let finding = filter(copy(g:gitfix_findings), {_, v -> v.id == a:1})[0]
  
  if empty(finding) || empty(get(finding, 'suggested_fix', ''))
    call s:error('No fix available for this finding')
    return
  endif
  
  let filepath = get(finding, 'file_path', '')
  let line = get(finding, 'line_start', 1)
  let fix = get(finding, 'suggested_fix', '')
  
  try
    execute 'edit ' . fnameescape(filepath)
    call cursor(line, 1)
    let range_start = line - 1
    let range_end = get(find(get(finding, 'line_end', line), 0), line)
    execute range_start . ',' . range_end . 'delete _'
    call append(range_start - 1, split(finding.suggested_fix, '\n'))
    call GitFixDismissFinding(get(finding, 'id', ''))
    echom 'Fix applied successfully'
  catch
    call s:error('Failed to apply fix: ' . v:exception)
  endtry
endfunction

function! GitFixDismissFinding(finding_id) abort
  call s:notify('Dismissed finding ' . a:finding_id, 'info')
  call GitFixDismissFinding(a:finding_id)
endfunction

function! GitFixConfigure() abort
  call s:notify('Opening Git-Fix configuration...', 'info')
  execute 'edit' $HOME . '/.config/nvim/gitfix_config.lua'
endfunction

function! GitFixViewReport() abort
  if has('nvim')
    lua << EOF
    vim.ui.open('http://localhost:5173/report')
EOF
  else
    silent execute '!open http://localhost:5173/report 2>/dev/null || xdg-open http://localhost:5173/report 2>/dev/null || start http://localhost:5173/report'
  endif
endfunction

function! GitFixToggleAutoReview() abort
  let g:gitfix_config.auto_review = !g:gitfix_config.auto_review
  call s:notify('Auto-review ' . (g:gitfix_config.auto_review ? 'enabled' : 'disabled'), 'info')
endfunction

function! GitFixStatus() abort
  let status = 'Git-Fix Status:\n'
  let status .= '  Enabled: ' . (g:gitfix_config.enabled ? 'Yes' : 'No') . '\n'
  let status .= '  Auto-review: ' . (g:gitfix_config.auto_review ? 'On' : 'Off') . '\n'
  let status .= '  API URL: ' . g:gitfix_config.api_url . '\n'
  let status .= '  Languages: ' . join(g:gitfix_config.languages, ', ') . '\n'
  call s:notify(status, 'info')
endfunction

" =============================================================================
# Auto-commands
# =============================================================================

augroup GitFix
  autocmd!
  
  " Auto-scan on save
  autocmd BufWritePost * if g:gitfix_config.enabled && g:gitfix_config.auto_review && g:gitfix_config.scan_on_save
        \ | call GitFixScanCurrentFile()
        \ | endif
  
  " Scan on type (debounced)
  autocmd TextChanged,TextChangedI * if g:gitfix_config.enabled && g:gitfix_config.scan_on_type
        \ | call GitFixDebouncedScan()
        \ | endif
  
  " Clear diagnostics on buffer delete
  autocmd BufDelete * call GitFixClearDiagnostics(expand('<abuf>'))
  
  " Update diagnostics on buffer enter
  autocmd BufEnter * if g:gitfix_config.enabled
        \ | call GitFixRefreshDiagnostics()
        \ | endif
augroup END

let s:scan_timer = 0
function! GitFixDebouncedScan() abort
  if s:scan_timer > 0
    call timer_stop(s:scan_timer)
  endif
  let g:gitfix_debounce_ms = get(g:gitfix_config, 'scan_debounce_ms', 500)
  let s:scan_timer = timer_start(g:gitfix_debounce_ms, 'GitFixScanCurrentFile')
endfunction

function! GitFixRefreshDiagnostics() abort
  " Would need to re-fetch findings for current buffer
  " For now, just re-scan if enabled
  if g:gitfix_config.auto_review && g:gitfix_config.scan_on_save
    call GitFixScanCurrentFile()
  endif
endfunction

" =============================================================================
# Status Line
# =============================================================================

function! GitFixStatusLine() abort
  if !g:gitfix_config.enabled
    return ''
  endif
  
  let icon = '🔍'
  let status = 'Git-Fix'
  
  if exists('g:gitfix_ws_connected') && g:gitfix_ws_connected
    return '%#GitFixStatusConnected#' . icon . ' ' . status . '%*'
  else
    return '%#GitFixStatusDisconnected#' . icon . ' ' . status . ' (offline)%*'
  endif
endfunction

" Highlight groups
if has('nvim')
  lua << EOF
  vim.api.nvim_set_hl(0, 'GitFixStatusConnected', {fg = '#00ff00', bold = true})
  vim.api.nvim_set_hl(0, 'GitFixStatusDisconnected', {fg = '#ff00ff', bold = true})
  vim.api.nvim_set_hl(0, 'GitFixFindingCritical', {fg = '#ff3333', bold = true})
  vim.api.nvim_set_hl(0, 'GitFixFindingHigh', {fg = '#ff8c00', bold = true})
  vim.api.nvim_set_hl(0, 'GitFixFindingMedium', {fg = '#ff8c00'})
  vim.api.nvim_set_hl(0, 'GitFixFindingLow', {fg = '#00ff00'})
  vim.api.nvim_set_hl(0, 'GitFixFindingInfo', {fg = '#00ffff'})
EOF
endif

" =============================================================================
# Keymaps
# =============================================================================

nnoremap <silent> <leader>gf :GitFixScanFile<CR>
nnoremap <silent> <leader>gw :GitFixScanWorkspace<CR>
nnoremap <silent> <leader>gd :GitFixOpenDashboard<CR>
nnoremap <silent> <leader>gF :GitFixShowFindings<CR>
nnoremap <silent> <leader>gc :GitFixConfigure<CR>
nnoremap <silent> <leader>gr :GitFixViewReport<CR>
nnoremap <silent> <leader>gt :GitFixToggleAutoReview<CR>
nnoremap <silent> <leader>gs :GitFixStatus<CR>
nnoremap <silent> <leader>gc :GitFixConnect<CR>
nnoremap <silent> <leader>gd :GitFixDisconnect<CR>

" Visual mode
vnoremap <silent> <leader>gf :GitFixScanFile<CR>

" =============================================================================
# Initialize
# =============================================================================

function! GitFixInit() abort
  call s:log('Git-Fix initialized')
  call GitFixConnectWS()
endfunction

" Auto-initialize
autocmd VimEnter * call GitFixInit()

" =============================================================================
# Help
# =============================================================================

command! -nargs=0 GitFixHelp call GitFixShowHelp()

function! GitFixShowHelp() abort
  let help = "
Git-Fix Vim Plugin - Cyberpunk Code Review Engine

COMMANDS:
  :GitFixScanFile       - Scan current file
  :GitFixScanWorkspace  - Scan entire workspace
  :GitFixOpenDashboard  - Open web dashboard
  :GitFixShowFindings   - Show findings in quickfix
  :GitFixConfigure      - Open configuration
  :GitFixViewReport     - View full report
  :GitFixToggleAutoReview - Toggle auto-review
  :GitFixStatus         - Show status
  :GitFixConnect        - Connect WebSocket
  :GitFixDisconnect     - Disconnect WebSocket
  :GitFixHelp           - Show this help

KEYMAPS:
  <leader>gf  - Scan current file
  <leader>gw  - Scan workspace
  :GitFixOpenDashboard  - Open dashboard
  <leader>gF  - Show findings
  <leader>gc  - Configure
  <leader>gr  - View report
  <leader>gt  - Toggle auto-review
  <leader>gs  - Show status
  <leader>gc  - Connect
  <leader>gd  - Disconnect

CONFIGURATION:
  Add to your init.vim/init.lua:
  
  let g:gitfix_config = {
    \ 'api_url': 'http://localhost:5000',
    \ 'ws_url': 'ws://localhost:5000/ws',
    \ 'enabled': 1,
    \ 'auto_review': 1,
    \ 'severity_threshold': 'medium',
    \ 'languages': ['python', 'typescript', 'javascript', 'go', 'rust', 'java', 'cpp'],
    \ 'scan_on_save': 1,
    \ 'scan_on_type': 0,
    \ 'scan_debounce_ms': 500,
    \ 'show_inline_annotations': 1,
    \ 'show_status_bar': 1,
    \ 'realtime_updates': 1,
    \ }

HELP:
  :GitFixHelp - Show this help
"
  echom help
endfunction

" =============================================================================
# Setup
# =============================================================================

" Create highlight groups
highlight default link GitFixFindingCritical Error
highlight default link GitFixFindingHigh Error
highlight default link GitFixFindingMedium Warning
highlight default link GitFixFindingLow Info
highlight default link GitFixFindingInfo Hint

" Finish
finish
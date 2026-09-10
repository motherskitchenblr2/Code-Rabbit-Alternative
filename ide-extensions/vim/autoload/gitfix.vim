" =============================================================================
# Git-Fix Vim Autoload Functions
# =============================================================================

if exists('g:loaded_gitfix_autoload')
  finish
endif
let g:loaded_gitfix_autoload = 1

if !exists('g:gitfix_config')
  let g:gitfix_config = {}
endif

let g:gitfix_config_default = {
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

function! gitfix#setup(config) abort
  if a:0 > 0
    let g:gitfix_config = extend(deepcopy(g:gitfix_config_default), a:config, 'force')
  else
    let g:gitfix_config = deepcopy(g:gitfix_config_default)
  endif
  
  call gitfix#init()
endfunction

function! gitfix#init() abort
  call gitfix#log('Git-Fix initialized')
  call gitfix#connect_ws()
endfunction

function! gitfix#scan_current_file() abort
  if !gitfix#should_scan()
    return
  endif
  
  let code = join(getline(1, '$'), "\n")
  let language = &filetype
  let filepath = expand('%:p')
  
  if empty(code)
    call gitfix#notify('File is empty', 'info')
    return
  endif
  
  call gitfix#notify('Scanning ' . expand('%:t') . '...', 'info')
  
  try
    let result = gitfix#api_request('POST', '/api/v1/scan', {
          \ 'code': code,
          \ 'language': &filetype,
          \ 'file_path': expand('%:p'),
        \ })
    if has_key(result, 'findings')
      call gitfix#update_diagnostics(bufnr('%'), result.findings)
      call gitfix#notify('Scan complete: ' . len(result.findings) . ' findings', 'info')
    endif
  catch
    call gitfix#error('Scan failed: ' . v:exception)
  endtry
endfunction

function! gitfix#scan_workspace() abort
  let files = split(globpath('.', '**', 0, 1), '\n')
  let filtered = filter(copy(files), {idx, f -> 
        \ f !~# 'node_modules' && f !~# '\.git' && 
        \ f !~# '\.min\.js$' && f !~# '\.min\.css$' &&
        \ f !~# 'vendor' && f !~# 'dist' && f !~# 'build'
      \})
  
  if empty(filtered)
    call gitfix#notify('No files to scan', 'info')
    return
  endif
  
  let total = len(filtered)
  let scanned = 0
  
  for file in filtered
    try
      let code = readfile(fnameescape(f), 'b')
      let ft = matchstr(f, '\.[^.]*$')[1:]
      call gitfix#scan_code(join(f, "\n"), ft, f)
      let scanned += 1
      echon "\rScanning: " . scanned . "/" . total . " files"
      redraw
    catch
      call gitfix#warn("Failed to scan " . v:val . ": " . v:exception)
    endtry
  endfor
  
  echon "\r"
  call gitfix#notify('Workspace scan complete: ' . scanned . ' files scanned', 'info')
endfunction

function! gitfix#scan_code(code, language, filepath) abort
  let payload = {
        \ 'code': a:code,
        \ 'language': a:language,
        \ 'file_path': a:filepath,
      \ }
  return gitfix#api_request('POST', '/api/v1/scan', payload)
endfunction

function! gitfix#api_request(method, endpoint, data) abort
  let url = gitfix#get_api_url() . a:endpoint
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
  let cmd .= ' ' . shellescape(gitfix#get_api_url() . a:endpoint)
  
  let output = system(cmd)
  if v:shell_error
    call gitfix#error('API request failed: ' . output)
    return {}
  endif
  return json_decode(output)
endfunction

function! gitfix#get_api_url() abort
  return get(g:gitfix_config, 'api_url', 'http://localhost:5000')
endfunction

function! gitfix#connect_ws() abort
  if has('nvim')
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
    call gitfix#warn('WebSocket not fully supported in Vim. Use Neovim for real-time updates.')
  endif
endfunction

function! gitfix#disconnect_ws() abort
  if has('nvim')
    lua << EOF
    if vim.g.gitfix_ws then
      vim.g.gitfix_ws:close()
      vim.g.gitfix_ws = nil
    end
EOF
  endif
endfunction

function! gitfix#update_diagnostics(bufnr, findings) abort
  if !has('nvim')
    return
  endif
  
  if a:bufnr == 0
    let bufnr = bufnr('%')
  endif
  
  let diagnostics = []
  for finding in a:findings
    let line = get(finding, 'line_start', get(finding, 'line', 1)) - 1
    let end_line = get(finding, 'line_end', get(finding, 'line', 1)) - 1
    let severity = get(finding, 'severity', 'info')
    
    let diagnostic = {
          \ 'lnum': line,
          \ 'end_lnum': end_line,
          \ 'col': 0,
          \ 'end_col': 100,
          \ 'severity': gitfix#map_severity(severity),
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
  
  call nvim_buf_set_diagnostic(a:bufnr, gitfix#get_ns_id(), diagnostics)
endfunction

function! gitfix#map_severity(severity) abort
  let map = {
        \ 'critical': 1,
        \ 'high': 1,
        \ 'medium': 2,
        \ 'low': 3,
        \ 'info': 4,
      \ }
  return get(map, a:severity, 4)
endfunction

function! gitfix#get_ns_id() abort
  if !exists('g:gitfix_ns_id')
    let g:gitfix_ns_id = nvim_create_namespace('GitFix')
  endif
  return g:gitfix_ns_id
endfunction

function! gitfix#clear_diagnostics(bufnr) abort
  if has('nvim') && a:bufnr > 0
    call nvim_buf_clear_namespace(a:bufnr, gitfix#get_ns_id(), 0, -1)
  endif
endfunction

function! gitfix#notify(msg, level) abort
  if has('nvim')
    call luaeval('vim.notify(_A[1], _A[2])', [a:msg, a:level])
  else
    if a:level == 'error'
      echohl ErrorMsg
      echom '[Git-Fix] ' . a:msg
      echohl None
    elseif a:level == 'warn'
      echohl WarningMsg
      echom '[Git-Fix] ' . a:msg
      echohl None
    else
      echom '[Git-Fix] ' . a:msg
    endif
  endif
endfunction

function! gitfix#log(msg) abort
  call gitfix#notify(a:msg, 'info')
endfunction

function! gitfix#warn(msg) abort
  call gitfix#notify(a:msg, 'warn')
endfunction

function! gitfix#error(msg) abort
  call gitfix#notify(a:msg, 'error')
endfunction

function! gitfix#map_severity(severity) abort
  let map = {
        \ 'critical': 1,
        \ 'high': 1,
        \ 'medium': 2,
        \ 'low': 3,
        \ 'info': 4,
      \ }
  return get(map, a:severity, 4)
endfunction

function! gitfix#should_scan() abort
  if !get(g:gitfix_config, 'enabled', 1)
    return 0
  endif
  
  let ft = &filetype
  if index(get(g:gitfix_config, 'languages', []), ft) == -1
    return 0
  endif
  
  if !get(g:gitfix_config, 'scan_dirty_files', 0) && &modified
    return 0
  endif
  
  let max_size = get(g:gitfix_config, 'max_file_size', 1048576)
  if line2byte(line('$') + 1) > max_size
    return 0
  endif
  
  let fname = expand('%:p')
  for pattern in get(g:gitfix_config, 'exclude_patterns', [])
    if fname =~# pattern
      return 0
    endif
  endfor
  
  return 1
endfunction

" =============================================================================
# User Commands
# =============================================================================

command! -nargs=0 GitFixScanFile call gitfix#scan_current_file()
command! -nargs=0 GitFixScanWorkspace call gitfix#scan_workspace()
command! -nargs=0 GitFixOpenDashboard call gitfix#open_dashboard()
command! -nargs=0 GitFixShowFindings call gitfix#show_findings()
command! -nargs=* GitFixApplyFix call gitfix#apply_fix(<f-args>)
command! -nargs=* GitFixDismissFinding call gitfix#dismiss_finding(<f-args>)
command! -nargs=0 GitFixConfigure call gitfix#configure()
command! -nargs=0 GitFixViewReport call gitfix#view_report()
command! -nargs=0 GitFixToggleAutoReview call gitfix#toggle_auto_review()
command! -nargs=0 GitFixStatus call gitfix#status()
command! -nargs=0 GitFixConnect call gitfix#connect_ws()
command! -nargs=0 GitFixDisconnect call gitfix#disconnect_ws()
command! -nargs=0 GitFixHelp call gitfix#help()

function! gitfix#apply_fix(args) abort
  if a:0 == 0
    call gitfix#error('Usage: GitFixApplyFix <finding_id>')
    return
  endif
  
  let finding_id = a:1
  let findings = g:gitfix_findings
  let finding = filter(copy(g:gitfix_findings), {_, v -> v.id == a:1})[0]
  
  if empty(finding) || empty(get(finding, 'suggested_fix', ''))
    call gitfix#error('No fix available for this finding')
    return
  endif
  
  let filepath = get(finding, 'file_path', '')
  let line = get(finding, 'line_start', 1)
  let fix = get(finding, 'suggested_fix', '')
  
  try
    execute 'edit ' . fnameescape(filepath)
    call cursor(line, 1)
    let range_start = line - 1
    let range_end = get(get(finding, 'line_end', line), 0, line)
    execute range_start . ',' . range_end . 'delete _'
    call append(range_start - 1, split(finding.suggested_fix, '\n'))
    call gitfix#dismiss_finding(get(finding, 'id', ''))
    call gitfix#notify('Fix applied successfully', 'info')
  catch
    call gitfix#error('Failed to apply fix: ' . v:exception)
  endtry
endfunction

function! gitfix#dismiss_finding(finding_id) abort
  call gitfix#notify('Dismissed finding ' . a:finding_id, 'info')
  call gitfix#api_request('DELETE', '/api/v1/findings/' . a:finding_id . '/dismiss', {})
endfunction

function! gitfix#open_dashboard() abort
  if has('nvim')
    lua << EOF
    vim.ui.open('http://localhost:5173')
EOF
  else
    silent execute '!open http://localhost:5173 2>/dev/null || xdg-open http://localhost:5173 2>/dev/null || start http://localhost:5173'
  endif
endfunction

function! gitfix#show_findings() abort
  let findings = g:gitfix_findings
  if empty(findings)
    call gitfix#notify('No findings available', 'info')
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

function! gitfix#configure() abort
  call gitfix#notify('Opening Git-Fix configuration...', 'info')
  execute 'edit' $HOME . '/.config/nvim/gitfix_config.lua'
endfunction

function! gitfix#view_report() abort
  if has('nvim')
    lua << EOF
    vim.ui.open('http://localhost:5173/report')
EOF
  else
    silent execute '!open http://localhost:5173/report 2>/dev/null || xdg-open http://localhost:5173/report 2>/dev/null || start http://localhost:5173/report'
  endif
endfunction

function! gitfix#toggle_auto_review() abort
  let g:gitfix_config.auto_review = !g:gitfix_config.auto_review
  call gitfix#notify('Auto-review ' . (g:gitfix_config.auto_review ? 'enabled' : 'disabled'), 'info')
endfunction

function! gitfix#status() abort
  let status = 'Git-Fix Status:\n'
  let status .= '  Enabled: ' . (get(g:gitfix_config, 'enabled', 1) ? 'Yes' : 'No') . '\n'
  let status .= '  Auto-review: ' . (get(g:gitfix_config, 'auto_review', 1) ? 'On' : 'Off') . '\n'
  let status .= '  API URL: ' . get(g:gitfix_config, 'api_url', 'http://localhost:5000') . '\n'
  let status .= '  Languages: ' . join(get(g:gitfix_config, 'languages', []), ', ') . '\n'
  call gitfix#notify(status, 'info')
endfunction

function! gitfix#help() abort
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
  <leader>gd  - Open dashboard
  <leader>gF  - Show findings
  <leader>gc  - Configure
  <leader>gr  - View report
  <leader>gt  - Toggle auto-review
  <leader>gs  - Show status

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
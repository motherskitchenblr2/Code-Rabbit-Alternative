with open('.github/workflows/security.yml', 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)
    
    # Check if this line contains checkout@v4
    if 'uses: actions/checkout@v4' in line:
        # Look ahead to see if token is already configured
        j = i + 1
        has_token = False
        while j < len(lines):
            next_line = lines[j]
            if 'token:' in next_line and 'GITHUB_TOKEN' in next_line:
                has_token = True
                break
            if not next_line.startswith(' ') and not next_line.startswith('\t') and next_line.strip() != '':
                break
            j += 1
        
        if not has_token:
            # Check if there's a with: block next
            if i + 1 < len(lines) and 'with:' in lines[i + 1].strip():
                # There's a with block, insert after fetch-depth
                inserted = False
                for k in range(i + 1, min(i + 10, len(lines))):
                    if 'fetch-depth:' in lines[k]:
                        # Insert after this line
                        lines.insert(k + 1, '          token: ${{ secrets.GITHUB_TOKEN }}\n')
                        lines.insert(k + 2, '          persist-credentials: true\n')
                        break
            else:
                # No with block, add one after checkout line
                lines.insert(i + 1, '        with:\n')
                lines.insert(i + 2, '          fetch-depth: 0\n')
                lines.insert(i + 4, '          token: ${{ secrets.GITHUB_TOKEN }}\n')
                lines.insert(i + 5, '          persist-credentials: true\n')
    
    i += 1

with open('.github/workflows/security.yml', 'w') as f:
    f.writelines(lines)

print("Done")
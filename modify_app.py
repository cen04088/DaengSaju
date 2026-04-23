import re

with open(r'c:\Users\SSAFY\Desktop\새 폴더\saju\frontend\src\app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove lockReports() call
content = content.replace('        // Re-lock the report on every new result\n        lockReports();', '        // Re-lock the report on every new result')
content = content.replace('        lockReports();\n        lockChemReport();', '        lockChemReport();')

# Remove function lockReports()
pattern_lock = re.compile(r'  function lockReports\(\) \{[\s\S]*?(?=\n  function lockChemReport\(\))', re.MULTILINE)
content = re.sub(pattern_lock, '', content)

# Remove function unlockReports()
pattern_unlock = re.compile(r'  function unlockReports\(\) \{[\s\S]*?(?=\n  function unlockChemReport\(\))', re.MULTILINE)
content = re.sub(pattern_unlock, '', content)

# Remove btnUnlock event listener block
pattern_btn = re.compile(r'  const btnUnlock = document\.getElementById\(\'btn-unlock-report\'\);[\s\S]*?(?=\n  const btnUnlockChem = document\.getElementById\(\'btn-unlock-chem\'\);)', re.MULTILINE)
content = re.sub(pattern_btn, '', content)

with open(r'c:\Users\SSAFY\Desktop\새 폴더\saju\frontend\src\app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print('Modified app.js')

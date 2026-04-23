import re

with open(r'c:\Users\SSAFY\Desktop\새 폴더\saju\frontend\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove locked-container class
content = content.replace('<div id="locked-reports-container" class="locked-container">', '<div id="locked-reports-container">')

# Remove lockable-text class from the 4 p tags
content = content.replace('<p id="res-food" class="lockable-text"', '<p id="res-food"')
content = content.replace('<p id="res-energy" class="lockable-text"', '<p id="res-energy"')
content = content.replace('<p id="res-love" class="lockable-text"', '<p id="res-love"')
content = content.replace('<p id="res-social" class="lockable-text"', '<p id="res-social"')

# Remove unlock-overlay for general saju
pattern = re.compile(r'<!-- Unlock Overlay \(visible while locked\) -->\s*<div id="unlock-overlay" class="unlock-overlay">[\s\S]*?</button>\s*</div>\s*</div>', re.MULTILINE)
content = re.sub(pattern, '', content)

with open(r'c:\Users\SSAFY\Desktop\새 폴더\saju\frontend\index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Modified index.html')

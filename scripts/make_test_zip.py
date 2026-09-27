"""Create a deterministic, explicitly synthetic fixture for browser tests."""
import sys
from pathlib import Path
import zipfile
files = {
    'README.md': '# Synthetic verification fixture\nNot a live repository analysis.\n',
    'src/main.py': '# Synthetic fixture; never execute imported code.\n' + ''.join(f'value_{i} = {i}\n' for i in range(2, 451)) + '''
def validate_email(value):
    return "@" in value

def is_valid_email(address):
    return "@" in address

def check_email(candidate):
    return "@" in candidate

def send_email(address):
    return validate_email(address)

def orphaned_helper(value):
    return value.strip()
''',
    'src/unknown.custom': '<script>globalThis.sourceExecuted = true</script>\nSafe unknown-language text.\n',
    'src/caller.py': 'from main import validate_email\nvalidate_email("person@example.com")\n',
    'src/util.js': 'export function sharedHelper() { return 1; }\n',
    'src/caller.js': 'import {sharedHelper} from "./util.js";\nsharedHelper();\n',
    'docs/guide.md': '# Guide\nSynthetic file.\n',
    'assets/binary.bin': b'\x00\x01\x02',
    '.env': 'SYNTHETIC_TEST_VALUE=not-a-real-secret',
    'broken.py': 'def invalid syntax\n',
    'empty.txt': '',
}
target = Path(sys.argv[1])
target.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for path, data in files.items():
        info = zipfile.ZipInfo(path, (2026, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, data)

from importlib import metadata
from pathlib import Path
import swiftbot

print('module_file=', Path(swiftbot.__file__).resolve())
print('package_version=', metadata.version('swiftbot'))
print('package_summary=', metadata.metadata('swiftbot').get('Summary'))
print('python_requires=', metadata.metadata('swiftbot').get('Requires-Python'))
print('requires=')
for requirement in metadata.requires('swiftbot') or []:
    print('  ', requirement)
print('exports=', sorted(name for name in dir(swiftbot) if not name.startswith('_')))
print('submodules=')
package_dir = Path(swiftbot.__file__).resolve().parent
for path in sorted(package_dir.glob('*.py')):
    print('  ', path.name, path.stat().st_size)

# SwiftBot installation notes

Installation command used:

```text
python3 -m venv /home/ubuntu/swiftbot-benchmark/venv-swiftbot
/home/ubuntu/swiftbot-benchmark/venv-swiftbot/bin/python -m pip install --upgrade pip
/home/ubuntu/swiftbot-benchmark/venv-swiftbot/bin/python -m pip install swiftbot
```

The installation completed successfully on the sandbox’s Python 3.12 runtime. Installed package version is `1.6.3`; `pip check` reported `No broken requirements found`. The package requires Python `>=3.10`, `aiohttp>=3.10,<4.0`, and `httpx[http2]>=0.27,<0.29`.

The import verification succeeded from `swiftbot/__init__.py`. Public exports include `SwiftBot`, `TestClient`, `FakePool`, `Message`, `CallbackQuery`, `Filters`, `Composer`, `Pipeline`, `Dialogue`, `Wizard`, `Reply`, `Scope`, `storage`, `throttle`, and the typed model/update modules. The package’s installed Python source modules occupy approximately 250 KB by summing the listed `.py` files, excluding bytecode and dependencies.

The benchmark environment is at `/home/ubuntu/swiftbot-benchmark/venv-swiftbot` and can be reused without reinstallation.

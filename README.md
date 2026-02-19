
Step 1: Get Token.json from https://cm.fabric-testbed.net

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel setuptools
pip install fabrictestbed-extensions
```

Run script
```bash
source /home/lucas/code2025/learning-fabric-testbed/.venv/bin/activate.fish
source /home/lucas/code2025/learning-fabric-testbed/fabric_config/fabric_rc
```

Bastion key refresh (required periodically for SSH)
```bash
source /home/lucas/code2025/learning-fabric-testbed/fabric_config/fabric_rc
python /home/lucas/code2025/learning-fabric-testbed/renew_bastion_keys.py
```

File Tree
```bash
.
├── create_slice.py
├── fabric_config
│  ├── fabric_bastion_key
│  ├── fabric_bastion_key.pub
│  ├── fabric_rc
│  ├── slice_key
│  ├── slice_key.pub
│  └── token.json
├── import_keys_from_windows.sh
├── list_slices.py
├── README.md
├── renew_bastion_keys.py
└── write_fabric_rc.sh
```

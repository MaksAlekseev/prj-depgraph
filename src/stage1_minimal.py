import sys
import configparser
from pathlib import Path
import argparse

def load_config(path):
    cfg = configparser.ConfigParser()
    if not Path(path).exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    cfg.read(path, encoding='utf-8')
    if 'main' not in cfg:
        raise KeyError("Section [main] is missing in config file")
    return cfg['main']

def validate_and_normalize(main):
    out = {}
    pkg = main.get('package_name', '').strip()
    test_mode = main.getboolean('test_repo_mode', fallback=False)
    repo = main.get('repo_url', '').strip()
    if not pkg:
        raise ValueError("package_name is required in config")
    if not repo and not test_mode:
        raise ValueError("Either repo_url must be set or test_repo_mode = true")
    out['package_name'] = pkg
    out['repo_url'] = repo
    out['test_repo_mode'] = str(test_mode)
    out['ascii_tree'] = str(main.getboolean('ascii_tree', fallback=False))
    out['filter_substring'] = main.get('filter_substring', '')
    return out

def print_kv(dct):
    for k, v in dct.items():
        print(f"{k}={v}")

def main(config_path):
    try:
        main_section = load_config(config_path)
        validated = validate_and_normalize(main_section)
        print_kv(validated)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', default='config.ini', help='Path to INI config')
    args = parser.parse_args()
    main(args.config)
import sys
import configparser
from pathlib import Path
import argparse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

def load_config(path):
    cfg = configparser.ConfigParser()
    if not Path(path).exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    cfg.read(path, encoding='utf-8')
    if 'main' not in cfg:
        raise KeyError("Section [main] is missing in config file")
    return cfg['main']

def parse_package_name(pkg):
    # Ожидается формат groupId:artifactId:version
    parts = pkg.split(':')
    if len(parts) != 3:
        raise ValueError("package_name must be in format groupId:artifactId:version")
    group, artifact, version = parts
    return group.strip(), artifact.strip(), version.strip()

def build_pom_url(repo_url, group, artifact, version):
    # repo_url обычно заканчивается на '/', но учитываем оба варианта
    base = repo_url.rstrip('/') + '/'
    group_path = group.replace('.', '/') + '/'
    pom_name = f"{artifact}-{version}.pom"
    url = base + group_path + artifact + '/' + version + '/' + pom_name
    return url

def download_pom(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            content = resp.read()
            return content
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP error {e.code} when requesting {url}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error when requesting {url}: {e.reason}")

def extract_direct_dependencies_from_pom(pom_bytes):
    # Парсим XML и находим прямые зависимости
    try:
        root = ET.fromstring(pom_bytes)
    except ET.ParseError as e:
        raise RuntimeError(f"POM parse error: {e}")

    # Ищем все dependency элементы в дереве (с учётом namespace)
    deps = []
    for dep in root.findall('.//{*}dependency'):
        gid = dep.find('{*}groupId')
        aid = dep.find('{*}artifactId')
        ver = dep.find('{*}version')
        scope = dep.find('{*}scope')

        gid_text = gid.text.strip() if gid is not None and gid.text else '?'
        aid_text = aid.text.strip() if aid is not None and aid.text else '?'
        ver_text = ver.text.strip() if ver is not None and ver.text else '?'
        scope_text = scope.text.strip() if scope is not None and scope.text else ''

        entry = f"{gid_text}:{aid_text}:{ver_text}"
        if scope_text:
            entry += f" [{scope_text}]"
        deps.append(entry)
    return deps

def read_test_repo(file_path):
    """
    Format:
      A: B,C
      B: D,E
      C: F
      D:
      E: C
    Returns adjacency dict {node: [dep1,dep2,...]}
    """
    d = {}
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Test repo file not found: {file_path}")
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            name, deps = line.split(':', 1)
            name = name.strip()
            deps_list = [x.strip() for x in deps.split(',') if x.strip()]
            d[name] = deps_list
        else:
            # Если без ":", считаем, что у узла нет зависимостей
            d[line] = []
    return d

def print_list(label, lst):
    print(f"--- {label} ({len(lst)}) ---")
    for item in lst:
        print(item)

def main(config_path):
    try:
        main_section = load_config(config_path)
        test_mode = main_section.getboolean('test_repo_mode', fallback=False)
        if test_mode:
            # Читаем тестовый файл, выводим зависимости для package_name (корневого узла)
            test_file = main_section.get('test_file', 'examples/test_repo_A.txt')
            graph = read_test_repo(test_file)
            root_pkg = main_section.get('package_name', '').strip()
            if not root_pkg:
                # Если package_name пуст, возьмём первый ключ
                root_pkg = next(iter(graph.keys()), None)
            if root_pkg is None:
                print("No packages in test repository.")
                return
            deps = graph.get(root_pkg, [])
            print(f"Test mode ON. Root package: {root_pkg}")
            print_list("Direct dependencies", deps)
            return

        # production mode: скачиваем pom.xml
        pkg = main_section.get('package_name', '').strip()
        repo = main_section.get('repo_url', '').strip()
        if not pkg:
            raise ValueError("package_name is required in config")
        if not repo:
            raise ValueError("repo_url is required in config when not in test mode")

        group, artifact, version = parse_package_name(pkg)
        url = build_pom_url(repo, group, artifact, version)
        print(f"Downloading POM from: {url}")
        pom = download_pom(url)
        deps = extract_direct_dependencies_from_pom(pom)
        print_list("Direct dependencies", deps)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Stage 2: collect direct dependencies from Maven POM or test repo")
    parser.add_argument('--config', '-c', default='config.ini', help='Path to INI config')
    args = parser.parse_args()
    main(args.config)

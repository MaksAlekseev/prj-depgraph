
# Проект: Система конфигурационного управления зависимостями (prj-depgraph)

## Описание проекта
Данный проект реализует многоэтапную систему конфигурационного управления,  
которая анализирует и визуализирует зависимости программных модулей.

Проект написан на языке Python и демонстрирует полный цикл работы  
— от считывания конфигурационных параметров до построения графа зависимостей  
и визуализации его в виде диаграммы.

Каждый этап оформлен как отдельная ветка в GitHub, что позволяет наглядно  
проследить развитие проекта с помощью системы контроля версий.

---

## Основные возможности
- Чтение настроек из конфигурационного файла config.ini  
- Загрузка реальных зависимостей из Maven Central Repository  
- Парсинг файлов pom.xml и извлечение прямых зависимостей  
- Построение графа зависимостей в текстовом виде  
- Вычисление порядка загрузки модулей (топологическая сортировка)  
- Обнаружение циклов зависимостей  
- Генерация Mermaid-диаграммы (graph.mmd) для визуализации графа  
- Возможность работы в тестовом и реальном режиме

---

## Структура проекта
```

prj-depgraph/
│
├── src/
│   └── main.py              # основной код проекта
│
├── examples/
│   └── test_repo_A.txt      # тестовые данные для оффлайн-режима
│
├── config.ini               # конфигурационный файл
├── graph.mmd                # визуализация зависимостей (генерируется автоматически)
├── README.md                # описание проекта
└── .gitignore

```

---

## Конфигурация (config.ini)
Пример файла конфигурации:

```

[main]
package_name = com.google.code.gson:gson:2.10.1
repo_url = [https://repo1.maven.org/maven2/](https://repo1.maven.org/maven2/)
test_repo_mode = false
test_file = examples/test_repo_A.txt
ascii_tree = true

```

Пояснения параметров:

| Параметр | Назначение |
|-----------|------------|
| package_name | Имя пакета Maven (groupId:artifactId:version) |
| repo_url | URL репозитория Maven |
| test_repo_mode | Включает тестовый режим (true/false) |
| test_file | Файл с тестовыми зависимостями (для offline режима) |
| ascii_tree | Вывод дерева зависимостей в ASCII-формате |

---

## Запуск проекта
В терминале (из корня проекта):

```

python src/main.py --config config.ini

```

Пример вывода:
```

Root package: com.google.code.gson:gson:2.10.1
Mode: REAL

--- Dependency graph (text) ---
com.google.code.gson:gson:2.10.1 -> com.google.guava:guava:32.0.1-jre, org.checkerframework:checker-qual:3.27.0
com.google.guava:guava:32.0.1-jre -> com.google.guava:failureaccess:1.0.1, com.google.guava:listenablefuture:9999.0-empty-to-avoid-conflict-with-guava, com.google.code.findbugs:jsr305:3.0.2
...

--- Safe load order ---

1. com.google.guava:failureaccess:1.0.1
2. com.google.guava:listenablefuture:9999.0-empty-to-avoid-conflict-with-guava
3. com.google.code.findbugs:jsr305:3.0.2
4. org.checkerframework:checker-qual:3.27.0
5. com.google.guava:guava:32.0.1-jre
6. com.google.code.gson:gson:2.10.1

Mermaid diagram saved to: graph.mmd
You can view it on [https://mermaid.live/](https://mermaid.live/)

```

---

## Визуализация зависимостей
После выполнения программы создаётся файл graph.mmd.  
Он содержит диаграмму зависимостей в формате Mermaid.

Пример содержимого файла:

```

graph TD
"com.google.code.gson:gson:2.10.1" --> "com.google.guava:guava:32.0.1-jre"
"com.google.code.gson:gson:2.10.1" --> "org.checkerframework:checker-qual:3.27.0"
"com.google.guava:guava:32.0.1-jre" --> "com.google.guava:failureaccess:1.0.1"
"com.google.guava:guava:32.0.1-jre" --> "com.google.guava:listenablefuture:9999.0-empty-to-avoid-conflict-with-guava"
"com.google.guava:guava:32.0.1-jre" --> "com.google.code.findbugs:jsr305:3.0.2"

```

Чтобы просмотреть диаграмму:
1. Перейдите на сайт https://mermaid.live  
2. Вставьте содержимое файла graph.mmd в окно редактора  
3. Нажмите Generate Diagram  
4. На экране появится визуальный граф зависимостей

---

## Этапы проекта

| Этап | Ветка Git | Краткое описание |
|------|------------|------------------|
| 1 | stage-1-minimal-prototype | Базовая структура проекта, чтение config.ini |
| 2 | stage-2-data-collection | Загрузка и парсинг POM-файлов |
| 3 | stage-3-graph-ops | Построение графа зависимостей |
| 4 | stage-4-loading-order | Вычисление порядка загрузки модулей |
| 5 | stage-5-visualization | Генерация визуальной диаграммы зависимостей |

---

## Используемые технологии
- Python 3.12  
- PyCharm — среда разработки  
- Git / GitHub — управление версиями и ветвями проекта  
- Mermaid — визуализация графов зависимостей  
- Maven Central Repository — источник реальных данных о зависимостях

---

## Использование на защите
Каждый этап реализован как отдельная ветка Git.  
Переключение между этапами выполняется через командную строку:  

```

git checkout stage-3-graph-ops

```

Запуск программы осуществляется в PyCharm командой:  

```

python src/main.py --config config.ini

```

Таким образом, можно пошагово показать развитие проекта —  
от конфигурации до визуализации зависимостей.

---

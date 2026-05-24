const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

/**
 * 1. ФУНКЦИЯ АВТОМАТИЧЕСКОГО ПОИСКА ИНТЕРПРЕТАТОРА
 * Ищет команду в текущем PATH или читает свежие данные напрямую из реестра Windows.
 */
function findRupythonExecutable() {
    // Сначала пробуем вызвать команду напрямую в окружении VS Code
    try {
        execSync('rupython --version', { stdio: 'ignore' });
        return 'rupython';
    } catch (e) {
        // Команда не ответила глобально, переходим к глубокому поиску в реестре
    }

    // Поиск для Windows по путям из реестра (как на вашем скриншоте)
    if (process.platform === 'win32') {
        try {
            const registryOutput = execSync('reg query HKCU\\Environment /v Path', { encoding: 'utf8' });
            const match = registryOutput.match(/Path\s+REG_(?:EXPAND_)?SZ\s+(.+)/i);

            if (match && match[1]) {
                const rawPathString = match[1].trim();
                const paths = rawPathString.split(';');

                for (let p of paths) {
                    let folder = p.trim();
                    if (!folder) continue;

                    // Раскрываем системные переменные, если они есть в пути
                    folder = folder.replace(/%([^%]+)%/g, (_, varName) => {
                        return process.env[varName.toUpperCase()] || process.env[varName.toLowerCase()] || `%${varName}%`;
                    });

                    const fullExePath = path.join(folder, 'rupython.exe');

                    if (fs.existsSync(fullExePath)) {
                        console.log(`[RuPy] Успешно найден по пути из реестра: ${fullExePath}`);
                        return fullExePath;
                    }
                }
            }
        } catch (registryError) {
            console.error('[RuPy] Ошибка чтения реестра Windows:', registryError);
        }
    }

    return null;
}

function activate(context) {
    console.log('Расширение RuPy активно!');

    // --- 2. ЗАГРУЗКА БАЗЫ ИЗ JSON ---
    const modulesPath = path.join(context.extensionPath, 'modules.json');
    let modulesData = {};

    try {
        if (!fs.existsSync(modulesPath)) {
            fs.writeFileSync(modulesPath, JSON.stringify({}, null, 4), 'utf8');
            console.log('Создан новый файл modules.json');
        }
        const fileContent = fs.readFileSync(modulesPath, 'utf8');
        if (fileContent.trim()) {
            modulesData = JSON.parse(fileContent);
        }
    } catch (err) {
        console.error('Ошибка при работе с modules.json:', err);
        vscode.window.showErrorMessage('Ошибка инициализации базы данных модулей');
        modulesData = {};
    }

    // Стили подсветки синтаксиса
    const importDecorationType = vscode.window.createTextEditorDecorationType({
        color: '#4EC9B0',
        fontWeight: 'bold'
    });
    const funcDecorationType = vscode.window.createTextEditorDecorationType({
        color: '#DCDCAA'
    });

    // --- 3. ФУНКЦИЯ ПОДСВЕТКИ ---
    function updateDecorations() {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== 'rupy') return;

        const text = editor.document.getText();
        const importDecs = []; // Для названий модулей (Зеленый)
        const keywordDecs = []; // Для ключевого слова "использовать" (Розовый)
        const funcDecs = [];

        for (const [pyMod, modData] of Object.entries(modulesData)) {
            if (!modData) continue;
            const ruMod = modData["ru-name"] || pyMod;

            // --- БЛОК 1: ПОДСВЕТКА ИМПОРТА (использовать время) ---
            // Здесь две группы: m[1] = "использовать", m[2] = имя модуля
            const importRegEx = new RegExp(`(использовать)\\s+(${ruMod})(?![\\w\\а-яА-ЯёЁ])`, 'g');
            let m;
            while ((m = importRegEx.exec(text)) !== null) {
                if (!m[1] || !m[2]) continue; // Защита от пустых совпадений

                const fullMatchIndex = m.index;
                const keywordText = m[1]; // "использовать"
                const moduleText = m[2];  // например, "время"

                const moduleStartIndex = fullMatchIndex + m[0].indexOf(moduleText);

                keywordDecs.push({
                    range: new vscode.Range(
                        editor.document.positionAt(fullMatchIndex),
                        editor.document.positionAt(fullMatchIndex + keywordText.length)
                    )
                });

                importDecs.push({
                    range: new vscode.Range(
                        editor.document.positionAt(moduleStartIndex),
                        editor.document.positionAt(moduleStartIndex + moduleText.length)
                    )
                });
            }

            // --- БЛОК 2: ПОДСВЕТКА ФУНКЦИЙ И ИХ МОДУЛЕЙ (время.время) ---
            if (text.includes(`использовать ${ruMod}`) && modData.sources) {
                for (const [pySrc, srcData] of Object.entries(modData.sources)) {
                    if (!srcData) continue;

                    const ruSrc = srcData["ru-name"] || pySrc;
                    const escapedRuSrc = ruSrc.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');

                    // Регулярное выражение захватывает: 
                    // m[1] — имя модуля (время)
                    // m[2] — имя функции (время)
                    const funcRegEx = new RegExp(`(?:^|[^\\w\\а-яА-ЯёЁ])(${ruMod})\\s*\\.\\s*(${escapedRuSrc})(?![\\w\\а-яА-ЯёЁ])`, 'g');

                    let fm;
                    while ((fm = funcRegEx.exec(text)) !== null) {
                        if (!fm[1] || !fm[2]) continue;

                        const fullMatchText = fm[0];
                        const moduleNameText = fm[1];   // Первое слово "время"
                        const functionNameText = fm[2]; // Второе слово "время"
                        const fullMatchIndex = fm.index;

                        // 1. Находим позицию названия модуля и добавляем в ЗЕЛЕНУЮ подсветку
                        const modStartIndex = fullMatchIndex + fullMatchText.indexOf(moduleNameText);
                        importDecs.push({
                            range: new vscode.Range(
                                editor.document.positionAt(modStartIndex),
                                editor.document.positionAt(modStartIndex + moduleNameText.length)
                            )
                        });

                        // 2. Находим позицию функции (после точки) и добавляем в подсветку ФУНКЦИЙ
                        const funcStartIndex = fullMatchIndex + fullMatchText.lastIndexOf(functionNameText);
                        funcDecs.push({
                            range: new vscode.Range(
                                editor.document.positionAt(funcStartIndex),
                                editor.document.positionAt(funcStartIndex + functionNameText.length)
                            )
                        });
                    }
                }
            }


        }


        // Применяем стили к редактору
        editor.setDecorations(importDecorationType, importDecs); // Название модуля (Зеленый)
        editor.setDecorations(funcDecorationType, funcDecs);

        // ВАЖНО: Если у вас еще не объявлен стиль для розового цвета, 
        // мы можем использовать встроенный или создать новый, но сейчас применим его к импортам
        if (typeof keywordDecorationType !== 'undefined') {
            editor.setDecorations(keywordDecorationType, keywordDecs);
        }
    }

    // --- 4. ДИНАМИЧЕСКИЕ ПОДСКАЗКИ (СНИППЕТЫ С ОПИСАНИЕМ) ---

    // Провайдер №1: Подсказки названий модулей через пробел
    let moduleNameProvider = vscode.languages.registerCompletionItemProvider('rupy', {
        provideCompletionItems(document, position) {
            const linePrefix = document.lineAt(position).text.substr(0, position.character);

            if (!linePrefix.endsWith('использовать ') && !linePrefix.endsWith('из ')) {
                return undefined;
            }

            const completions = [];
            for (const [pyMod, modData] of Object.entries(modulesData)) {
                const ruMod = modData["ru-name"];
                if (ruMod) {
                    const item = new vscode.CompletionItem(ruMod, vscode.CompletionItemKind.Module);
                    item.detail = `Модуль RuPy (Python: ${pyMod})`;

                    const docMarkdown = new vscode.MarkdownString();
                    docMarkdown.appendMarkdown(`Импортирует встроенный модуль \`${ruMod}\`.\n\n`);
                    docMarkdown.appendMarkdown(`* Оригинальный модуль Python: \`${pyMod}\``);
                    item.documentation = docMarkdown;

                    completions.push(item);
                }
            }
            return completions;
        }
    }, ' ');

        // Провайдер №2: Подсказки функций через точку с динамической подгрузкой документации
    let moduleFunctionsProvider = vscode.languages.registerCompletionItemProvider('rupy', {
        async provideCompletionItems(document, position) {
            const linePrefix = document.lineAt(position).text.substr(0, position.character);
            
            // ИСПРАВЛЕНО: Убрали лишний \$ на конце регулярного выражения
            const match = linePrefix.match(/([\а-яА-ЯёЁ\w]+)\s*\.\s*$/);
            if (!match) return undefined;

            const ruModName = match[1]; // Извлекаем имя модуля перед точкой
            let pyMod = null;
            let modData = null;

            // ИСПРАВЛЕНО: Проверяем как русское, так и английское название модуля
            for (const [key, data] of Object.entries(modulesData)) {
                if (key === ruModName || (data && data["ru-name"] === ruModName)) {
                    pyMod = key;
                    modData = data;
                    break;
                }
            }

            // Если модуля нет в нашей базе modules.json, пробуем использовать его имя напрямую как pyMod
            if (!pyMod) {
                pyMod = ruModName;
                modData = modulesData[pyMod] || {};
            }

            const ruMod = (modData && modData["ru-name"]) || pyMod;
            const completions = [];
            const sources = (modData && modData.sources) || {};

            // Сначала смотрим заготовленные переводы из modules.json
            for (const [pySrc, srcData] of Object.entries(sources)) {
                const ruSrc = srcData["ru-name"] || pySrc;
                const item = new vscode.CompletionItem(ruSrc, vscode.CompletionItemKind.Function);

                item.insertText = new vscode.SnippetString(`${ruSrc}(\${1})`);
                item.detail = `Функция из модуля ${ruMod}`;

                item.data = {
                    pyMod: pyMod,
                    pySrc: pySrc,
                    ruMod: ruMod,
                    ruSrc: ruSrc,
                    fallbackDesc: srcData.description || ''
                };

                completions.push(item);
            }

            // Если в JSON пусто или это сторонний модуль, запрашиваем список методов у Python НАПРЯМУЮ,
            // чтобы окно IntelliSense не оставалось пустым (как на скриншоте)
            if (completions.length === 0) {
                const pythonCmd = getPythonCommand();
                const pythonScript = `
import ${pyMod}
import json
methods = []
for name in dir(${pyMod}):
    if name.startswith('_'): continue
    try:
        if callable(getattr(${pyMod}, name)): methods.append(name)
    except: continue
print(json.dumps(methods))
                `.strip().replace(/\n/g, '; ');

                try {
                    const { stdout } = await execAsync(`"${pythonCmd}" -c "${pythonScript}"`, { timeout: 1000 });
                    const dynamicMethods = JSON.parse(stdout.trim());

                    for (const pySrc of dynamicMethods) {
                        const item = new vscode.CompletionItem(pySrc, vscode.CompletionItemKind.Function);
                        item.insertText = new vscode.SnippetString(`${pySrc}(\${1})`);
                        item.detail = `Динамическая функция из ${pyMod}`;
                        
                        item.data = {
                            pyMod: pyMod,
                            pySrc: pySrc,
                            ruMod: pyMod,
                            ruSrc: pySrc,
                            fallbackDesc: ''
                        };
                        completions.push(item);
                    }
                } catch (e) {
                    console.error("[RuPy] Не удалось динамически прочитать модуль через Python:", e);
                }
            }

            return completions;
        }
    }, '.');

    // ЭТАП 2 ДЛЯ ПРОВАЙДЕРА №2: Загрузка docstring (Оставляем асинхронной без изменений)
    moduleFunctionsProvider.resolveCompletionItem = async function (item) {
        if (!item.data) return item;

        const { pyMod, pySrc, ruMod, ruSrc, fallbackDesc } = item.data;
        const pythonCmd = getPythonCommand();
        const docMarkdown = new vscode.MarkdownString();

        docMarkdown.appendMarkdown(`### ${ruMod}.${ruSrc}(\u2026)\n`);
        docMarkdown.appendMarkdown(`___\n`);
        docMarkdown.appendMarkdown(`* **Оригинал в Python:** \`${pyMod}.${pySrc}\`\n\n`);

        try {
            const pythonScript = `
import ${pyMod}
import inspect
import json
obj = getattr(${pyMod}, '${pySrc}')
sig = ''
try: sig = str(inspect.signature(obj))
except: pass
doc = getattr(obj, '__doc__', '') or ''
print(json.dumps({'sig': sig, 'doc': doc.strip()}))
            `.strip().replace(/\n/g, '; ');

            const { stdout } = await execAsync(`"${pythonCmd}" -c "${pythonScript}"`, { timeout: 800 });
            const result = JSON.parse(stdout.trim());

            if (result.sig) {
                docMarkdown.value = `### ${ruMod}.${ruSrc}${result.sig}\n___\n* **Оригинал в Python:** \`${pyMod}.${pySrc}\`\n\n`;
            }

            if (result.doc && result.doc !== 'None') {
                docMarkdown.appendMarkdown(`**Документация модуля:**\n\`\`\`text\n${result.doc}\n\`\`\``);
            } else if (fallbackDesc) {
                docMarkdown.appendMarkdown(`**Документация модуля:**\n\`\`\`text\n${fallbackDesc}\n\`\`\``);
            } else {
                docMarkdown.appendMarkdown(`*У этого метода встроенное описание в Python отсутствует.*`);
            }
        } catch (e) {
            if (fallbackDesc) {
                docMarkdown.appendMarkdown(`**Документация модуля:**\n\`\`\`text\n${fallbackDesc}\n\`\`\``);
            } else {
                docMarkdown.appendMarkdown(`*Оригинальное системное описание недоступно.*`);
            }
        }

        item.documentation = docMarkdown;
        return item;
    };




    // --- 5. КОМАНДА ЗАПУСКА КОДА ---
    let runCommand = vscode.commands.registerCommand('rupy.run', async function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        if (editor.document.isUntitled) {
            const uri = await vscode.window.showSaveDialog({
                filters: { 'RuPy Files': ['rupy'] },
                title: 'Сохранить файл перед запуском'
            });
            if (!uri) return;
            fs.writeFileSync(uri.fsPath, editor.document.getText(), 'utf8');
        } else {
            await editor.document.save();
        }

        const config = vscode.workspace.getConfiguration('rupy');
        // ИСПРАВЛЕНО: Теперь ключ "path" совпадает с тем, что объявлено в package.json (rupy.path)
        let rupythonPath = config.get('path') || 'rupython';

        // ИСПОЛЬЗОВАНИЕ УМНОГО ПОИСКА
        if (rupythonPath === 'rupython') {
            const detectedPath = findRupythonExecutable();

            if (detectedPath) {
                rupythonPath = detectedPath;
                // Автоматически сохраняем найденный путь, чтобы больше не выполнять тяжелый поиск по файловой системе
                await config.update('path', rupythonPath, vscode.ConfigurationTarget.Global);
            } else {
                const choice = await vscode.window.showErrorMessage(
                    'Команда "rupython" не найдена автоматически. Указать путь к файлу вручную?',
                    'Выбрать .exe файл', 'Отмена'
                );

                if (choice === 'Выбрать .exe файл') {
                    const exeUri = await vscode.window.showOpenDialog({
                        canSelectMany: false,
                        filters: { 'Исполняемые файлы': ['exe'] },
                        title: 'Выберите файл rupython.exe'
                    });

                    if (exeUri && exeUri[0]) {
                        rupythonPath = exeUri[0].fsPath;
                        await config.update('path', rupythonPath, vscode.ConfigurationTarget.Global);
                    } else {
                        return;
                    }
                } else {
                    return;
                }
            }
        }
        const terminal = vscode.window.activeTerminal || vscode.window.createTerminal("RuPy");
        terminal.show();

        // Проверяем, какой терминал запущен. Если это PowerShell (pwsh/powershell), добавляем оператор '&'
        const terminalName = (terminal.name || '').toLowerCase();
        const isPowerShell = terminalName.includes('powershell') || terminalName.includes('pwsh') || process.platform === 'win32';

        if (isPowerShell) {
            // Для PowerShell: & "путь" "аргумент"
            terminal.sendText(`& "${rupythonPath}" "${editor.document.fileName}"`);
        } else {
            // Для CMD, Bash, Zsh: "путь" "аргумент"
            terminal.sendText(`"${rupythonPath}" "${editor.document.fileName}"`);
        }

    });
    // --- 6. СОЗДАНИЕ НОВОГО ФАЙЛА RUPY ---
    let createNewFileCommand = vscode.commands.registerCommand('rupy.createNewFile', async function () {
        const doc = await vscode.workspace.openTextDocument({ language: 'rupy', content: 'вывести "Привет мир!"\n' });
        await vscode.window.showTextDocument(doc);
    });
    // --- 7. РЕГИСТРАЦИЯ ВСЕХ ПОДПИСОК И СЛУШАТЕЛЕЙ СТИЛЕЙ ---
    context.subscriptions.push(importDecorationType, funcDecorationType, moduleNameProvider, moduleFunctionsProvider, runCommand, createNewFileCommand, vscode.workspace.onDidChangeTextDocument(() => updateDecorations()), vscode.window.onDidChangeActiveTextEditor(() => updateDecorations()));
    if (vscode.window.activeTextEditor) {
        updateDecorations();

    }
}
function deactivate() { }

module.exports = { activate, deactivate };

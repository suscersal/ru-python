const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');


class RuPyFormattingProvider {
    provideDocumentFormattingEdits(document, options, token) {
        const edits = [];
        const lineCount = document.lineCount;
        let indentLevel = 0;
        const tabSize = options.tabSize || 4;
        const indentString = options.insertSpaces ? ' '.repeat(tabSize) : '\t';

        for (let i = 0; i < lineCount; i++) {
            const line = document.lineAt(i);
            if (line.isEmptyOrWhitespace) {
                // Оставляем пустые строки пустыми (без лишних пробелов)
                if (line.text.length > 0) {
                    edits.push(vscode.TextEdit.replace(line.range, ''));
                }
                continue;
            }

            let trimmedText = line.text.trim();

            // Логика уменьшения отступа для закрывающих конструкций (если они есть в RuPy)
            // Например, если строка начинается с "конец", "иначе", "выход" и т.д.
            if (trimmedText.startsWith('иначе') || trimmedText.startsWith('когда')) {
                indentLevel = Math.max(0, indentLevel - 1);
            }

            // Формируем правильный отступ для текущей строки
            const correctIndent = indentString.repeat(indentLevel);
            
            // Базовое форматирование пробелов внутри строки:
            // 1. Ставим ровно по одному пробелу вокруг операторов (=, +, -, *, /, ==)
            // 2. Убираем пробелы перед запятыми и двоеточиями, оставляем один ПОСЛЕ
            let formattedText = trimmedText
                .replace(/\s*([=\+\-\*\/]|==)\s*/g, ' $1 ') // Пробелы вокруг операторов
                .replace(/\s*([:,])\s*/g, '$1 ')            // Пробел строго ПОСЛЕ знаков препинания
                .replace(/\s+/g, ' ');                     // Схлопывание двойных пробелов

            // Восстанавливаем строку с правильным отступом
            const newLineText = correctIndent + formattedText.trim();

            if (line.text !== newLineText) {
                edits.push(vscode.TextEdit.replace(line.range, newLineText));
            }

            // Логика увеличения отступа для СЛЕДУЮЩЕЙ строки
            // Например, если текущая строка заканчивается двоеточием (как в Python) или ключевым словом
            if (trimmedText.endsWith(':') || trimmedText.startsWith('если') || trimmedText.startsWith('функция')) {
                indentLevel++;
            }
        }

        return edits;
    }
}






/**
 * 1. ФУНКЦИЯ АВТОМАТИЧЕСКОГО ПОИСКА ИНТЕРПРЕТАТОРА
 * Ищет команду в текущем PATH или читает свежие данные напрямую из реестра Windows.
 */
function findRupythonExecutable() {
    // Вытаскиваем готовый PATH из памяти процесса (работает мгновенно)
    const pathEnv = process.env.PATH || process.env.Path || '';
    if (!pathEnv) return null;

    // Разделяем пути в зависимости от ОС (в Windows разделитель ';', в Linux/Mac ':')
    const delimiter = process.platform === 'win32' ? ';' : ':';
    const paths = pathEnv.split(delimiter);

    for (let p of paths) {
        let folder = p.trim();
        if (!folder) continue;

        // Формируем имя файла под нужную ОС
        const exeName = process.platform === 'win32' ? 'rupython.exe' : 'rupython';
        const fullExePath = path.join(folder, exeName);

        // fs.existsSync работает с кэшем ОС и проверяет файл за доли миллисекунды
        try {
            if (fs.existsSync(fullExePath)) {
                console.log(`[RuPy] Успешно найден исполняемый файл: ${fullExePath}`);
                return fullExePath;
            }
        } catch (e) {
            // Пропускаем папки, к которым нет доступа
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
        const keywordDecs = []; // Для ключевых слов (Розовый)
        const funcDecs = []; // Для названий функций (Синий/Желтый)

        for (const [pyMod, modData] of Object.entries(modulesData)) {
            if (!modData) continue;
            const ruMod = modData["ru-name"] || pyMod;

            // --- БЛОК 1: ПОДСВЕТКА ИМПОРТА (использовать время [как в]) ---
            // Теперь выражение может опционально захватывать "как <алиас>"
            const importRegEx = new RegExp(`(использовать)\\s+(${ruMod})(?:\\s+(как)\\s+([\\w\\а-яА-ЯёЁ]+))?(?![\\w\\а-яА-ЯёЁ])`, 'g');
            let m;
            while ((m = importRegEx.exec(text)) !== null) {
                if (!m[1] || !m[2]) continue;

                const fullMatchIndex = m.index;
                const fullMatchText = m[0];
                const keywordText = m[1]; // "использовать"
                const moduleText = m[2];  // например, "время"

                // Подсвечиваем "использовать"
                keywordDecs.push({
                    range: new vscode.Range(
                        editor.document.positionAt(fullMatchIndex + fullMatchText.indexOf(keywordText)),
                        editor.document.positionAt(fullMatchIndex + fullMatchText.indexOf(keywordText) + keywordText.length)
                    )
                });

                // Подсвечиваем имя модуля
                const moduleStartIndex = fullMatchIndex + fullMatchText.indexOf(moduleText);
                importDecs.push({
                    range: new vscode.Range(
                        editor.document.positionAt(moduleStartIndex),
                        editor.document.positionAt(moduleStartIndex + moduleText.length)
                    )
                });

                // Если в строке есть слово "как" (группа m[3])
                if (m[3]) {
                    const asText = m[3]; // "как"
                    const aliasText = m[4]; // например, "д"

                    // Подсвечиваем "как" в розовый
                    const asStartIndex = fullMatchIndex + fullMatchText.indexOf(asText);
                    keywordDecs.push({
                        range: new vscode.Range(
                            editor.document.positionAt(asStartIndex),
                            editor.document.positionAt(asStartIndex + asText.length)
                        )
                    });

                    // Алиас подсвечиваем в зеленый (или синий, по вашему выбору — пусть пока будет в importDecs)
                    const aliasStartIndex = fullMatchIndex + fullMatchText.lastIndexOf(aliasText);
                    importDecs.push({
                        range: new vscode.Range(
                            editor.document.positionAt(aliasStartIndex),
                            editor.document.positionAt(aliasStartIndex + aliasText.length)
                        )
                    });
                }
            }

            // --- БЛОК 2: ПОДСВЕТКА ФУНКЦИЙ И ИХ МОДУЛЕЙ (время.время) ---
            if (modData.sources) { // Убрал strict-проверку на 'использовать', чтобы подсвечивало и при 'из ... использовать'
                for (const [pySrc, srcData] of Object.entries(modData.sources)) {
                    if (!srcData) continue;

                    const ruSrc = srcData["ru-name"] || pySrc;
                    const escapedRuSrc = ruSrc.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');

                    const funcRegEx = new RegExp(`(?:^|[^\\w\\а-яА-ЯёЁ])(${ruMod})\\s*\\.\\s*(${escapedRuSrc})(?![\\w\\а-яА-ЯёЁ])`, 'g');

                    let fm;
                    while ((fm = funcRegEx.exec(text)) !== null) {
                        if (!fm[1] || !fm[2]) continue;

                        const fullMatchText = fm[0];
                        const moduleNameText = fm[1];   
                        const functionNameText = fm[2]; 
                        const fullMatchIndex = fm.index;

                        const modStartIndex = fullMatchIndex + fullMatchText.indexOf(moduleNameText);
                        importDecs.push({
                            range: new vscode.Range(
                                editor.document.positionAt(modStartIndex),
                                editor.document.positionAt(modStartIndex + moduleNameText.length)
                            )
                        });

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

                        // --- БЛОК 3: ПОДСВЕТКА СЛОЖНОГО ИМПОРТА (из время использовать время [как в]) ---
            if (modData.sources) {
                for (const [pySrc, srcData] of Object.entries(modData.sources)) {
                    if (!srcData) continue;

                    const ruSrc = srcData["ru-name"] || pySrc;
                    const escapedRuSrc = ruSrc.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');

                    // Захватывает структуру: из (1) модуль (2) использовать (3) функция (4) [как (5) алиас (6)]
                    const fromRegEx = new RegExp(`\\b(из)\\s+(${ruMod})\\s+(использовать)\\s+(${escapedRuSrc})(?:\\s+(как)\\s+([\\w\\а-яА-ЯёЁ]+))?\\b`, 'g');
                    
                    let exM;
                    while ((exM = fromRegEx.exec(text)) !== null) {
                        const fullMatchIndex = exM.index;
                        const fullMatchText = exM[0];
                        
                        const izText = exM[1];        // "из"
                        const modText = exM[2];       // "время" (модуль)
                        const useText = exM[3];       // "использовать"
                        const funcText = exM[4];      // "время" (функция)

                        // 1. Подсвечиваем "из" (Розовый)
                        const izRelIndex = fullMatchText.indexOf(izText);
                        const izStart = fullMatchIndex + izRelIndex;
                        keywordDecs.push({ range: new vscode.Range(editor.document.positionAt(izStart), editor.document.positionAt(izStart + izText.length)) });

                        // 2. Подсвечиваем модуль (Зеленый)
                        const modRelIndex = fullMatchText.indexOf(modText);
                        const modStart = fullMatchIndex + modRelIndex;
                        importDecs.push({ range: new vscode.Range(editor.document.positionAt(modStart), editor.document.positionAt(modStart + modText.length)) });

                        // 3. Подсвечиваем "использовать" (Розовый)
                        const useRelIndex = fullMatchText.indexOf(useText, modRelIndex + modText.length);
                        const useStart = fullMatchIndex + useRelIndex;
                        keywordDecs.push({ range: new vscode.Range(editor.document.positionAt(useStart), editor.document.positionAt(useStart + useText.length)) });

                        // 4. Подсвечиваем функцию (Зеленый)
                        const funcRelIndex = fullMatchText.indexOf(funcText, useRelIndex + useText.length);
                        const funcStart = fullMatchIndex + funcRelIndex;
                        funcDecs.push({ range: new vscode.Range(editor.document.positionAt(funcStart), editor.document.positionAt(funcStart + funcText.length)) });

                        // 5. Если в конце строки есть конструкция "как алиас" (группы 5 и 6)
                        if (exM[5] && exM[6]) {
                            const asText = exM[5];     // "как"
                            const aliasText = exM[6];  // "а"

                            // Подсвечиваем "как" (Розовый) — считаем индекс ОТНОСИТЕЛЬНО строки совпадения
                            const asRelIndex = fullMatchText.indexOf(asText, funcRelIndex + funcText.length);
                            const asStart = fullMatchIndex + asRelIndex;
                            keywordDecs.push({ range: new vscode.Range(editor.document.positionAt(asStart), editor.document.positionAt(asStart + asText.length)) });

                            // Подсвечиваем алиас (Зеленый)
                            const aliasRelIndex = fullMatchText.lastIndexOf(aliasText);
                            const aliasStart = fullMatchIndex + aliasRelIndex;
                            funcDecs.push({ range: new vscode.Range(editor.document.positionAt(aliasStart), editor.document.positionAt(aliasStart + aliasText.length)) });
                        }
                    }
                }
            }


        }

        // Применяем стили к редактору
        editor.setDecorations(importDecorationType, importDecs); 
        editor.setDecorations(funcDecorationType, funcDecs);

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




    // Регистрируем форматировщик для файлов с селектором 'rupy'
    const formattingProvider = vscode.languages.registerDocumentFormattingEditProvider(
        { scheme: 'file', language: 'rupy' }, 
        new RuPyFormattingProvider()
    );

    context.subscriptions.push(formattingProvider);




// --- 5. КОМАНДА ЗАПУСКА КОДА ---
let runCommand = vscode.commands.registerCommand('rupy.run', async function () {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;

    // 1. Быстрое сохранение файла
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
    let rupythonPath = config.get('path') || 'rupython';

    // 2. Умный поиск (запускается ТОЛЬКО если путь не настроен)
    if (rupythonPath === 'rupython') {
        // Если findRupythonExecutable тяжелая, она выполнится только 1 раз за всё время
        const detectedPath = findRupythonExecutable();

        if (detectedPath) {
            rupythonPath = detectedPath;
            // Сохраняем без await, чтобы не ждать диск
            config.update('path', rupythonPath, vscode.ConfigurationTarget.Global);
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
                    config.update('path', rupythonPath, vscode.ConfigurationTarget.Global);
                } else {
                    return;
                }
            } else {
                return;
            }
        }
    }

    // 3. Мгновенная отправка в терминал
    const terminal = vscode.window.activeTerminal || vscode.window.createTerminal("RuPy");
    terminal.show(true);

    // Самая быстрая проверка PowerShell без обращений к API настроек
    const shellPath = (vscode.env.shell || '').toLowerCase();
    const isPowerShell = shellPath.includes('powershell') || shellPath.includes('pwsh') || shellPath.endsWith('powershell.exe');

    if (isPowerShell) {
        terminal.sendText(`& "${rupythonPath}" "${editor.document.fileName}"`);
    } else {
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

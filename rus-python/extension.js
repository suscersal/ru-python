const vscode = require('vscode');
const path = require('path');
const fs = require('fs');

function activate(context) {
    console.log('Расширение RuPy активно!');

    // --- 1. ЗАГРУЗКА БАЗЫ ИЗ JSON ---
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

    // Стили подсветки
    const importDecorationType = vscode.window.createTextEditorDecorationType({
        color: '#4EC9B0',
        fontWeight: 'bold'
    });
    const funcDecorationType = vscode.window.createTextEditorDecorationType({
        color: '#DCDCAA' 
    });

    // --- 2. ФУНКЦИЯ ПОДСВЕТКИ ---
    function updateDecorations() {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== 'rupy') return;

        const text = editor.document.getText();
        const importDecs = [];
        const funcDecs = [];

        for (const [pyMod, modData] of Object.entries(modulesData)) {
            const ruMod = modData["ru-name"] || pyMod;

            // Исправлено регулярное выражение для поддержки русских букв в границах слов
            const importRegEx = new RegExp(`использовать\\s+${ruMod}(?![\\w\\а-яА-ЯёЁ])`, 'g');
            let m;
            while ((m = importRegEx.exec(text))) {
                importDecs.push({ range: new vscode.Range(editor.document.positionAt(m.index), editor.document.positionAt(m.index + m.length)) });
            }

            if (text.includes(`использовать ${ruMod}`) && modData.sources) {
                for (const [pySrc, srcData] of Object.entries(modData.sources)) {
                    const ruSrc = srcData["ru-name"] || pySrc;
                    // Экранируем пробелы, если русское имя состоит из нескольких слов (например, "запись в каталоге")
                    const escapedRuSrc = ruSrc.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
                    const funcRegEx = new RegExp(`(?<=\\b${ruMod}\\.)${escapedRuSrc}(?![\\w\\а-яА-ЯёЁ])`, 'g');
                    
                    let fm;
                    while ((fm = funcRegEx.exec(text))) {
                        // Вычисляем точную позицию подсвечиваемого слова после точки
                        const startPos = fm.index;
                        funcDecs.push({ range: new vscode.Range(editor.document.positionAt(startPos), editor.document.positionAt(startPos + fm[0].length)) });
                    }
                }
            }
        }
        editor.setDecorations(importDecorationType, importDecs);
        editor.setDecorations(funcDecorationType, funcDecs);
    }

        // --- 3. ДИНАМИЧЕСКИЕ ПОДСКАЗКИ (СНИППЕТЫ С ОПИСАНИЕМ) ---
    
    // Провайдер №1: Подсказки названий модулей
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
                    
                    // ДОКУМЕНТАЦИЯ КАК В СНИППЕТАХ
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

    // Провайдер №2: Подсказки функций через точку с документацией
    let moduleFunctionsProvider = vscode.languages.registerCompletionItemProvider('rupy', {
        provideCompletionItems(document, position) {
            const linePrefix = document.lineAt(position).text.substr(0, position.character);
            
            for (const [pyMod, modData] of Object.entries(modulesData)) {
                const ruMod = modData["ru-name"] || pyMod;
                
                if (linePrefix.endsWith(`${ruMod}.`)) {
                    const completions = [];
                    const sources = modData["sources"] || {};
                    
                    for (const [pySrc, srcData] of Object.entries(sources)) {
                        const ruSrc = srcData["ru-name"] || pySrc;
                        const item = new vscode.CompletionItem(ruSrc, vscode.CompletionItemKind.Function);
                        
                        item.insertText = new vscode.SnippetString(`${ruSrc}(\${1})`);
                        item.detail = `Функция из модуля ${ruMod}`;
                        
                        // ДОКУМЕНТАЦИЯ КАК В СНИППЕТАХ
                        const docMarkdown = new vscode.MarkdownString();
                        docMarkdown.appendMarkdown(`### ${ruMod}.${ruSrc}(\u2026)\n`);
                        docMarkdown.appendMarkdown(`___\n`); // Горизонтальная линия
                        docMarkdown.appendMarkdown(`* **Оригинал:** \`${pyMod}.${pySrc}\`\n`);
                        
                        // Если в вашем modules.json у функции появится поле "description"
                        if (srcData.description) {
                            docMarkdown.appendMarkdown(`\n${srcData.description}`);
                        } else {
                            docMarkdown.appendMarkdown(`\n*Описание для этой функции еще не добавлено.*`);
                        }
                        
                        item.documentation = docMarkdown;
                        completions.push(item);
                    }
                    return completions;
                }
            }
            return undefined;
        }
    }, '.');


    // --- 4. ЗАПУСК ЧЕРЕЗ RUPYTHON ---
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
        let rupythonPath = config.get('path') || 'rupython';

        if (rupythonPath === 'rupython') {
            const { execSync } = require('child_process');
            try {
                execSync('rupython --version', { stdio: 'ignore' });
            } catch (e) {
                const choice = await vscode.window.showErrorMessage(
                    'Команда "rupython" не распознана. Указать путь к исполняемому файлу вручную?',
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
        terminal.sendText(`& "${rupythonPath}" "${editor.document.fileName}"`);
    });

    // --- 5. СОЗДАНИЕ НОВОГО ФАЙЛА RUPY ---
    let createNewFileCommand = vscode.commands.registerCommand('rupy.createNewFile', async function () {
        const doc = await vscode.workspace.openTextDocument({
            language: 'rupy',
            content: 'вывести "Привет мир!"\n'
        });
        await vscode.window.showTextDocument(doc);
    });

    // РЕГИСТРАЦИЯ ВСЕХ ПОДПИСОК
    context.subscriptions.push(
        moduleNameProvider,
        moduleFunctionsProvider,
        runCommand,
        createNewFileCommand,
        vscode.workspace.onDidChangeTextDocument(updateDecorations),
        vscode.window.onDidChangeActiveTextEditor(updateDecorations)
    );

    if (vscode.window.activeTextEditor) updateDecorations();
}

function deactivate() {}

module.exports = {activate, deactivate};

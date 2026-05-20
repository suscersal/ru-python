const vscode = require('vscode');
const path = require('path');
const fs = require('fs');

function activate(context) {
    console.log('Расширение RuPy активно!');

    // --- 1. ЗАГРУЗКА БАЗЫ ИЗ JSON (С АВТОСОЗДАНИЕМ) ---
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

        for (const [moduleName, data] of Object.entries(modulesData)) {
            const importRegEx = new RegExp(`использовать\\s+${moduleName}`, 'g');
            let m;
            while ((m = importRegEx.exec(text))) {
                importDecs.push({ range: new vscode.Range(editor.document.positionAt(m.index), editor.document.positionAt(m.index + m.length)) });
            }

            if (text.includes(`использовать ${moduleName}`) && data.функции) {
                for (const funcName of Object.keys(data.функции)) {
                    const funcRegEx = new RegExp(`${moduleName}\\.${funcName}`, 'g');
                    let fm;
                    while ((fm = funcRegEx.exec(text))) {
                        funcDecs.push({ range: new vscode.Range(editor.document.positionAt(fm.index), editor.document.positionAt(fm.index + fm.length)) });
                    }
                }
            }
        }
        editor.setDecorations(importDecorationType, importDecs);
        editor.setDecorations(funcDecorationType, funcDecs);
    }

    // --- 3. ДИНАМИЧЕСКИЕ СНИППЕТЫ ---
    let completionProvider = vscode.languages.registerCompletionItemProvider('rupy', {
        provideCompletionItems(document) {
            const text = document.getText();
            const completions = [];

            for (const [pyMod, modData] of Object.entries(modulesData)) {
                const ruMod = modData["ru-name"];
                if (text.includes(`использовать ${ruMod}`)) {
                    const sources = modData["sources"] || {};
                    for (const [pySrc, srcData] of Object.entries(sources)) {
                        const ruSrc = srcData["ru-name"];
                        const item = new vscode.CompletionItem(ruSrc, vscode.CompletionItemKind.Function);
                        item.insertText = new vscode.SnippetString(`${ruMod}.${ruSrc}(\${1})`);
                        item.detail = `Из модуля ${ruMod} (Python: ${pyMod}.${pySrc})`;
                        completions.push(item);
                    }
                }
            }
            return completions;
        }
    });

    // --- 4. ЗАПУСК ЧЕРЕЗ RUPYTHON (С ИСПРАВЛЕНИЕМ ОШИБКИ И ВЫБОРОМ EXE) ---
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
        // Символ & необходим для корректного вызова путей с кавычками в PowerShell
        terminal.sendText(`& "${rupythonPath}" "${editor.document.fileName}"`);
    });

        // --- 5. СОЗДАНИЕ НОВОГО ФАЙЛА RUPY (БЕЗ СОХРАНЕНИЯ НА ДИСК) ---
    let createNewFileCommand = vscode.commands.registerCommand('rupy.createNewFile', async function () {
        // Открываем пустой документ с привязкой к языку rupy, без жесткого пути к диску C:\
        const doc = await vscode.workspace.openTextDocument({
            language: 'rupy',
            content: 'вывести "Привет мир!"\n'
        });
        
        // Показываем его в редакторе
        await vscode.window.showTextDocument(doc);
    });



    // РЕГИСТРАЦИЯ ВСЕХ ПОДПИСОК (Исправлено)
    context.subscriptions.push(
        completionProvider,
        runCommand,
        createNewFileCommand,
        vscode.workspace.onDidChangeTextDocument(updateDecorations),
        vscode.window.onDidChangeActiveTextEditor(updateDecorations)
    );

    if (vscode.window.activeTextEditor) updateDecorations();
}

function deactivate() {}

module.exports = {activate, deactivate};
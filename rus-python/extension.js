const vscode = require('vscode');
const path = require('path');
const fs = require('fs');

function activate(context) {
    console.log('Расширение RuPy активно!');

    // --- 1. ЗАГРУЗКА БАЗЫ ИЗ JSON (С ЗАЩИТОЙ) ---
    const modulesPath = path.join(context.extensionPath, 'modules.json');
    let modulesData = {}; // По умолчанию пустой объект

    try {
        if (fs.existsSync(modulesPath)) {
            const fileContent = fs.readFileSync(modulesPath, 'utf8');
            if (fileContent) {
                modulesData = JSON.parse(fileContent);
            }
        } else {
            console.error('Файл modules.json не найден по пути:', modulesPath);
        }
    } catch (err) {
        console.error('Ошибка при чтении modules.json:', err);
        vscode.window.showErrorMessage('Ошибка в формате файла modules.json');
        modulesData = {}; // Сбрасываем, чтобы не было ошибки "null to object"
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

        // Безопасный перебор (Object.entries теперь точно получит объект)
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
            
            // Если в тексте есть "использовать время"
            if (text.includes(`использовать ${ruMod}`)) {
                const sources = modData["sources"] || {};
                
                for (const [pySrc, srcData] of Object.entries(sources)) {
                    const ruSrc = srcData["ru-name"];
                    const item = new vscode.CompletionItem(ruSrc, vscode.CompletionItemKind.Function);
                    
                    // Вставляем: время.пауза($1)
                    item.insertText = new vscode.SnippetString(`${ruMod}.${ruSrc}(\${1})`);
                    item.detail = `Из модуля ${ruMod} (Python: ${pyMod}.${pySrc})`;
                    completions.push(item);
                    }
                }
            }
            return completions;
        }
    });

    // --- 4. ЗАПУСК ЧЕРЕЗ RUPYTHON ---
    let runCommand = vscode.commands.registerCommand('rupy.run', function () {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        editor.document.save().then(() => {
            const terminal = vscode.window.activeTerminal || vscode.window.createTerminal("RuPy");
            terminal.show();
            terminal.sendText(`rupython "${editor.document.fileName}"`);
        });
    });

    context.subscriptions.push(
        completionProvider,
        runCommand,
        vscode.workspace.onDidChangeTextDocument(updateDecorations),
        vscode.window.onDidChangeActiveTextEditor(updateDecorations)
    );

    if (vscode.window.activeTextEditor) updateDecorations();
}

function deactivate() {}

module.exports = { activate, deactivate };

const vscode = require('vscode');
const path = require('path'); // <- ОБЯЗАТЕЛЬНО
const fs = require('fs');



/**
 * Метод активации: выполняется, когда VS Code запускает расширение
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    console.log('Расширение "RUS Python" успешно активировано!');

        // Команда для создания нового файла из меню
    let createFileName = vscode.commands.registerCommand('rupy.createNewFile', async () => {
        const doc = await vscode.workspace.openTextDocument({
            language: 'rupy',
            content: 'вывести "Привет, Мир!"\n'
        });
        
        // Открываем созданный файл в редакторе
        await vscode.window.showTextDocument(doc);
    });

    context.subscriptions.push(createFileName);

        // Подсказки при наведении (Hovers)
    let hoverProvider = vscode.languages.registerHoverProvider('rupy', {
        provideHover(document, position) {
            const range = document.getWordRangeAtPosition(position);
            const word = document.getText(range);

            // База описаний и примеров
            const hoverData = {
                'функция': '**Функция** — создает блок кода.\n\nПример:\n```rupy\nфункция привет имя\n  вывести "Привет, " + имя\nконец\n```',
                'класс': '**Класс** — создает шаблон объекта.\n\nПример:\n```rupy\nкласс Робот\n  создать имя\n    это.имя = имя\n  конец\nконец\n```',
                'вывести': '**Вывести** — печатает текст в консоль.\n\n`вывести "Привет"`',
                'добавить': '**добавить** — метод списка.\n\n`список.добавить значение`',
                'это': '**это** — обращение к текущему объекту (self).\n\n`это.имя = "Борис"`'
            };

            if (hoverData[word]) {
                return new vscode.Hover(hoverData[word]);
            }
        }
    });

    context.subscriptions.push(hoverProvider);


    // Регистрируем команду запуска, которую мы указали в package.json
    let disposable = vscode.commands.registerCommand('rupy.run', function () {
        const editor = vscode.window.activeTextEditor;
        
        // Проверяем, открыт ли файл
        if (!editor) {
            vscode.window.showErrorMessage("Ошибка: Нет активного файла для запуска.");
            return;
        }

        editor.document.save().then(async () => {
            const filePath = editor.document.fileName;
            const extensionPath = context.extensionPath;
            
            // 1. Проверяем, есть ли сохраненный путь в памяти расширения
            let exePath = context.globalState.get('rupyExePath');

            // 2. Если в памяти пусто или файл по этому пути исчез, ищем в папке расширения
            if (!exePath || !fs.existsSync(exePath)) {
                exePath = path.join(extensionPath, 'rupy.exe');
            }
            
            // 3. Если всё еще не нашли (нет ни в памяти, ни в папке), просим выбрать вручную
            if (!fs.existsSync(exePath)) {
                const choice = await vscode.window.showErrorMessage(
                    "Транслятор rupy.exe не найден. Выбрать вручную?",
                    "Да", "Отмена"
                );

                if (choice === "Да") {
                    const fileUri = await vscode.window.showOpenDialog({
                        canSelectMany: false,
                        openLabel: 'Выбрать rupy.exe',
                        filters: { 'Исполняемые файлы': ['exe'] }
                    });

                    if (fileUri && fileUri[0]) {
                        exePath = fileUri[0].fsPath;
                        // СОХРАНЯЕМ ПУТЬ В ПАМЯТЬ
                        await context.globalState.update('rupyExePath', exePath);
                        vscode.window.showInformationMessage("Путь к RuPy сохранен!");
                    } else {
                        return; 
                    }
                } else {
                    return;
                }
            }

            // 4. Запуск в терминале
            const terminal = vscode.window.activeTerminal || vscode.window.createTerminal("RuPy");
            terminal.show();
            terminal.sendText(`& "${exePath}" "${filePath}"`);
        });


    });

    context.subscriptions.push(disposable);
}

// Метод деактивации (выполняется при закрытии VS Code)
function deactivate() {}

module.exports = {
    activate,
    deactivate
};

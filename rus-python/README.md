[![Visual Studio Code](https://custom-icon-badges.demolab.com/badge/Visual%20Studio%20Code-0078d7.svg?logo=visualstudiocode&logoColor=white)](https://marketplace.visualstudio.com/items?itemName=suscersal.russ-python)
[![Marketplace Version](https://vsmarketplacebadges.dev/version-short/suscersal.russ-python.svg)](https://marketplace.visualstudio.com/items?itemName=suscersal.russ-python) 
[![Downloads](https://vsmarketplacebadges.dev/downloads-short/suscersal.russ-python.svg)](https://marketplace.visualstudio.com/items?itemName=suscersal.russ-python) 
[![Installs](https://vsmarketplacebadges.dev/installs-short/suscersal.russ-python.svg)](https://marketplace.visualstudio.com/items?itemName=suscersal.russ-python) 
[![Rating](https://vsmarketplacebadges.dev/rating-short/suscersal.russ-python.svg)](https://marketplace.visualstudio.com/items?itemName=suscersal.russ-python)
## Подробности по расширению.

* Самодельные snippets и самодельная русификация модулей [клик](https://github.com/suscersal/ru-python/blob/main/rus-python/README.md)

## Пример добавления кастомной русификации:
```
"module": {
    "ru-name": "модуль",
    "sources": {
      "func1": {
        "ru-name": "функция1"
      },
      "class1": {
        "ru-name": "класс 1"
      },
      "var1": {
        "ru-name": "переменная1"
      }
    }
  }
```
_ну в принципе можно посмотреть готовый [файл](https://github.com/suscersal/ru-python/blob/main/rus-python/modules.json) (буду не против комитов на дополнение(в будущем хочу реализовать добавление через сайт))._ 

_Вот скрипт на простой перевод: [тык](https://github.com/suscersal/ru-python/blob/main/rus-python/simple-add-modules.py)_

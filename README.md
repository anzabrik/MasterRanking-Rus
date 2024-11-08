# MasterRanking: Джанго-приложение, которое вычисляет лучшие книги и авторов на основе полученных от пользователя списков 

[Video Demo](https://youtu.be/VljTP1cG0S8) -- на русском

[Video Demo](https://youtu.be/4m2JK5gQPnw) -- in English

## Инструменты

Django, JavaScript, Python, SQLite, BootStrap.

## Общие сведения

МастерРейтинг -- это веб-приложение, которое определяет самые популярные книги и авторов на основании загруженных пользователем списков.

Пользователь создает тему и добавляет туда несколько списков книг по своему выбору, назначая каждому из списков "уровень доверия". Приложение, в свою очередь, выдает усредненный список, так называемый МастерРейтинг. В нем книги изо всех списков расположены по рейтингу. Рейтинг подсчитывается на основании нескольких факторов, включая количество упоминаний книги в списках, уровень доверия, количество книг в списке, место книги в списке. Дополнительно сразу же вычисляется рейтинг авторов в теме, который можно посмотреть на отдельной вкладке.

Приложение ничего не добавляет от себя: пользователь сам решает, как назвать тему, какие туда включить списки и какой уровень доверия им присвоить. Пользователь может удалять и редактировать любые элементы рейтинга на любом этапе, и в ответ рейтинг будет пересчитан.

## Модели

**Master** представляет всю тему (MasterRanking) в целом. В типичном сценарии первое действие пользователя после регистрации -- создать тему.

**List** представляет список книг. Связан с Master отношениями ManyToMany: в одной теме может быть несколько списков, а один список может входить в несколько тем.

**Author, Book**. Book связана с Author отношениями ManyToMany: у одной книги может быть много авторов, а один автор может написать много книг.

**Book\_In\_List** выполняет две главные функции:
- показывает, к какому списку относится некоторая книга (связь с Book и List представлена посредством ForeignKey);
- отображает значимость книги в данном списке: ее рейтинг и, если список ранжированный, то место в списке. У одной книги (Book) может быть только одна Book\_In\_List в отдельно взятом списке (List). Т.е., к примеру, если у нас "Приключения Геккльберри Финна" стоят на третьем месте в списке "Книги о дружбе из школьной программы", то не может эта же книга стоять в этом же списке на седьмом месте.

Назначение и структура модели **Author\_In\_List** сходна с Book\_In\_List, за исключением одного отличия. Если у одного автора несколько книг в одном и том же списке, то рейтинг Author\_In\_List суммирует рейтинг каждой из них. Т.е. если у Марка Твена в списке "Книги о дружбе из школьной программы" два произведения, "Приключения Тома Сойера" и "Приключения Геккльберри Финна", и эти книги имеют рейтинги соответственно 10 и 20, то Author\_In\_List (Марк Твен -- "Книги о дружбе") имеет рейтинг 30. Это нужно потому, что в итоговом МастерРейтинге у нас есть не только рейтинг книг, но и отдельный рейтинг авторов в теме.

**Book-In-Master, Author\_In\_Master** работают примерно так же, как 'Book/Author\_In\_List', только эти модели связывают книги и авторов с темой. В этих моделях хранится информация о том, какой рейтинг книга или автор имеют в данной теме. При этом рейтинг книги или автора в теме суммирует их рейтинги во всех списках данной темы.

## Подсчитываем рейтинг

1. Как только пользователь закончил добавление книг в первый список, мы считаем рейтинг **каждой книги в списке** посредством функции 'set\_bil\_rating' ('bil' -- сокращение 'book\_in\_list'). При этом используется один из двух подходов:

- неранжированный список: book\_in\_list.rating = list.credibility \* 10 (т.е. рейтинг всех книг в списке одинаковый и зависит от уровня доверия списку);
- ранжированный список: сначала мы считаем общий рейтинг списка: list.credibility \* list.book\_in\_list\_set.count() \* 10 (произведение уровня доверия и количества книг в списке). Затем, мы считаем так называемый 'atom\_count' ("количество атомов") для данного списка (это сумма всех мест в списке) и для каждой из книг (в зависимости от того, на каком месте книга). "Количество атомов" в списке должно быть равно сумме "количества атомов" всех входящих в него книг. Наконец, считаем рейтинг книги. Он зависит от "количества атомов" в данной книге и какой рейтинг у каждого атома: book\_in\_list.rating = book\_in\_list.atom\_count \* atom\_rating.

2. Рейтинг каждого **author\_in\_list** для нового списка рассчитывается в функции 'set\_ail\_rating'. Мы просто складываем рейтинги всех книг, которые автор имеет в этом списке.

3. Мы подсчитываем или пересчитываем рейтинг **книги или автора во всей теме** посредством функции 'reset\_bim\_aim\_rating' ('bim' –- сокращение 'book\_in\_master'). Она просто складывает рейтинги книги или автора из каждого списка в данной теме, включая новые и старые.

\*\*\*в некоторых формулах мы умножаем или делим значения на 10\*\*11, чтобы рейтинг был точнее.

## Как пользоваться приложением

Возьмем для примера воображаемого пользователя, Марию. Желая повысить свою продуктивность, она решает проверить, что полезного есть в книгах по этой теме. Поиск по книжным магазинам выдает тысячи результатов. И естественно, как почти любые результаты поиска и рейтинги, эти данные предвзяты и продвигают какие-то определенные книги вне зависимости от их реальной ценности для Марии.

Чтобы хоть в какой-то мере противодействовать этому, Мария обращается к нашему приложению, и оно выводит некое среднее арифметическое из нескольких книжных рейтингов. Давайте проследим за ее действиями после регистрации.

1. Стартовая страница для новых пользователей отображает мини-форму, куда Мария вводит только название темы (MasterRanking). Впоследствии, когда Мария добавит еще темы, стартовой страницей приложения для нее уже будет 'masters.htlm' -- она выводит все созданные пользователем темы.

2. Ну а пока Мария отправила название своей единственной темы, и приложение перенаправляет ее на страничку 'add\_list.html'. Здесь она заполняет:

- название списка;
- тему, к которой список относится (она сможет включить список в несколько тем, когда добавит еще темы)
- уровень доверия. Максимальное значение, 5 баллов, Мария назначит списку, что получила от подруги детства, которую считает идеалом продуктивности. А список из какого-то малопримечательного блога получит 1 балл. Когда Мария не уверена, как оценить уровень доверия тому или иному списку, приложение по умолчанию выставляет 3 балла;
- количество книг: определяет, сколько пустых форм для книг будет отображено на следующей странице (по умолчанию -- 10);
- ранжированный ли список;
- два не обязательных для заполнения поля: ссылка на список и заметки.

3. 'add\_books.html': Мария заполняет несколько форм для книг:

- колонка "Место" заполняется автоматически в ранжированных списках, но Мария может исправить цифры, если, к примеру, на одном месте сразу две книги;
- колонка "Авторы" не обязательна для заполнения. Для каждой книги Мария заполняет авторов только один раз -- если эта же книга встретится в другом списке, приложение само допишет автора, и эта информация будет отображаться на последующих страницах и учитываться в рейтинге авторов;
- в не обязательное для заполнения поле "Дополнительно" Мария может добавить, к примеру, краткое содержание или мнение автора рейтинга о книге -- они будут отображены в финальном МастерРейтинге.

4. Финальный МастерРейтинг рассчитывается и отображается даже если там только один список, чтобы Мария получила хоть какую-то компенсацию за свои усилия. Но полезным он станет только тогда, когда она добавит несколько списков.

5. Если Мария вносит изменения в списки, книги или перечень авторов, это обязательно отображается в МастерРейтинге. Если эти изменения влияют на рейтинг, то МастерРейтинг сразу же пересчитывается.

## Подход к повторяющимся названиям книг, списков, тем

Приложение запрещает повторяющиеся названия (дубли) для тем и списков, принадлежащих одному и тому же пользователю. Ему возвращают наполовину заполненную форму с объяснением, что нужно придумать уникальное название.

К названиям книг подход иной. Когда Мария добавляет вторую, третью и т.д. книгу с одинаковым названием, то приложение приписывает к заголовку индекс ("Суперкнига (1)", "Суперкнига (2)" и т.п.) Ведь в мире есть много книг с одинаковым названием, но разными авторами и содержанием, и мы не можем в нашем МастерРейтинге допустить слияния этих книг в одну. Индекс будет различать эти книги в приложении. Если же Мария действительно по ошибке добавит одну и ту же книгу, то заметит это по наличию индекса и сможет удалить книгу на любом этапе работы с приложением.

Места в ранжированных списках не уникальны. Ведь может случиться так, что у Марии в списке две книги одинаковой важности, и она хочет поставить их на одно и то же место. Благодаря этому приложение присвоит обеим книгам одинаковый рейтинг в финальном МастерРейтинге.

При этом другие пользователи, конечно же, могут использовать те же названия, что Мария, и это никак не повлияет на ее рейтинг. Ее книги, темы, списки принадлежат только ей.

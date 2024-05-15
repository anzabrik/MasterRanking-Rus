from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit

from crispy_bootstrap5.bootstrap5 import FloatingField
from .models import *


class MasterForm(forms.Form):
    name = forms.CharField(
        max_length = 960,
        label = 'Введите название (например, "Продуктивность")',
        )   
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'id-masterForm'
        self.helper.form_classs = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = ''
        self.helper.layout = Layout(FloatingField('name'))

        self.helper.add_input(Submit('submit', 'Save'))


class ListForm(forms.Form):
    name = forms.CharField(
        label = "Название списка",
        max_length = 320,  
    )

    masters = forms.ModelMultipleChoiceField(
        label = "МастерРэнкинг (вы можете выбрать более одного)",
        queryset = Master.objects.all(),
        #to_field_name = "name",
    )

    #Select field, empty_value = , normalizes to value of the type provided by coerce
    #Validates that the given value exists in the list of choices and can be coerced
    credibility = forms.TypedChoiceField(
        label = "Уровень доверия",
        choices = ((1, 1), (2, 2), (3, 3), (4, 4), (5,5)),
        coerce = lambda x: int(x),
        widget = forms.RadioSelect,
        initial = 3,
    )

    book_num = forms.IntegerField(
        label = "Количество книг",
        initial = 10,
        required = False,
    )
    
    places_matter = forms.BooleanField(
        label ="Это ранжированный список (первая книга лучшая)",
        required = False,
    )

    info = forms.CharField(
        label = "Дополнительно",
        max_length = 960,
        required = False,
    )

    url = forms.URLField(
        label = "Link",
        max_length = 560,
        required = False,  
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
       
        self.helper = FormHelper()
        self.helper.form_id = 'id-listForm'
        self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = ''      
        self.helper.add_input(Submit('submit', 'Save'))


class BookForm(forms.Form):
    place = forms.IntegerField(
        min_value = 1,
        required = False,             
    )
    
    title = forms.CharField(
        label = "Title",
        max_length = 320,                
    )

    authors = forms.CharField(
        label = "Автор/авторы через запятую. Если книга уже есть в других списках, это поле заполнится автоматически.",
        max_length = 960,
        required = False,
    )

    info = forms.CharField(
        label = "Дополнительно",
        max_length = 960,
        required = False,
    )


class BookFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.form_action = ''
        self.add_input(Submit('submit', 'Добавить эти книги'))
        self.template = 'bootstrap5/table_inline_formset.html'


class BookFormNoPlaces(forms.Form):
    title = forms.CharField(
        label = "Название",
        max_length = 320,
    )

    authors = forms.CharField(
        label = "Автор/авторы через запятую. Если книга уже есть в других списках, это поле заполнится автоматически.",
        max_length = 960,
        required = False,
    )

    info = forms.CharField(
        label = "Дополнительно",
        max_length = 960,
        required = False,
    )


class BookFormSetNoPlacesHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = 'post'
        self.form_action = ''
        self.add_input(Submit('submit', 'Добавить эти книги'))
        self.template = 'bootstrap5/table_inline_formset.html'
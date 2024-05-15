import json
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from .models import *
from .forms import *
from django.forms import formset_factory
from django.db.models import Max, Sum, Count
from crispy_forms.helper import FormHelper
from django.forms.models import model_to_dict
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


def get_redirected(queryset_or_class, lookups, validators):
    # Calls get_object_or_404 and conditionally builds redirect URL
    obj = get_object_or_404(queryset_or_class, **lookups)
    for key, value in validators.items():
        if value != getattr(obj, key):
            return obj, obj.get_absolute_url()
    return obj, None


def index(request):
    # If logged in - add new master or (if person has many masters) sees all masters
    if request.user.is_authenticated:
        if Master.objects.filter(user=request.user).count() > 4:
            return HttpResponseRedirect(reverse("masters"))
        return HttpResponseRedirect(reverse("master_add"))
    
    return render(request, "list/index.html")


@login_required
def master_add(request):
    if request.method == "POST":
        form = MasterForm(request.POST)
        if form.is_valid():
            try:           
                master = Master.objects.create(name=form.cleaned_data["name"], user=request.user)
            except:
                messages.error(request, "МастерРэнкинг под этим названием уже есть. Как насчет другого названия?")
                return render(request, "list/master_add.html",
                              {"form": form})
            else:
                messages.success(request, "МастерРэнкинг был создан.")
                return HttpResponseRedirect(reverse("list_add"))
        else:
            return render(request, "list/master_add.html", {"form": form})   
    return render(request, "list/master_add.html", {"form": MasterForm()})


@login_required
def list_add(request):
    if request.method == "POST":        
        form = ListForm(request.POST)
        if form.is_valid():
            # Use required fields to create a list
            try:
                l = List.objects.create(
                    name=form.cleaned_data["name"],
                    credibility = form.cleaned_data["credibility"],
                    places_matter = form.cleaned_data["places_matter"],
                    user=request.user
                    )
            except:
                messages.error(request, "Список под этим названием уже есть. Как насчет другого названия?")
                form = ListForm(request.POST)
                form.fields["masters"].queryset = Master.objects.filter(user=request.user).order_by("-time")
                return render(request, "list/list_add.html", {
                    "form": form})
            else:
                # Use optional fields to assign optional properties to the list
                if form.cleaned_data["info"]:
                    l.info = form.cleaned_data["info"]
                if form.cleaned_data["url"]:
                    l.url = form.cleaned_data["url"]              
                if form.cleaned_data["book_num"] and form.cleaned_data["book_num"] > 0:
                    l.book_num = form.cleaned_data["book_num"]
                else:
                   l.book_num = 10
                masters = form.cleaned_data["masters"] #queryset of master instances
                for master in masters.all():
                    if master.user != request.user:
                        raise Http404
                l.masters.add(*masters.all())
                l.save()
                messages.success(request, "Список был создан.")
                return HttpResponseRedirect(reverse("books_add", args=(l.id, l.slug)))
        form = ListForm(request.POST)
        form.fields["masters"].queryset = Master.objects.filter(user=request.user).order_by("-time")
        return render(request, "list/list_add.html", {"form": form})
    form = ListForm()
    form.fields["masters"].queryset = Master.objects.filter(user=request.user).order_by("-time")
    return render(request, "list/list_add.html", {"form": form})


@login_required
def list_edit(request, list_id, slug):
    try:
        l, list_url = get_redirected(List, {'pk': list_id}, {'slug': slug})
        if list_url:
            return HttpResponseRedirect(list_url)
    except:
        messages.error(request, "Такого списка не существует")
        return HttpResponseRedirect(reverse("lists"))
    if l.user != request.user:
        raise Http404
    list_form = ListForm(initial=model_to_dict(l))
    if request.method == "POST":
        list_form = ListForm(request.POST)
        if list_form.is_valid():
            # 1. Process fields that don't affect ratings
            l.name = list_form.cleaned_data["name"]
            l.info = list_form.cleaned_data["info"]
            l.url = list_form.cleaned_data["url"]
            if list_form.cleaned_data["book_num"] and list_form.cleaned_data["book_num"] > 0:
                l.book_num = list_form.cleaned_data["book_num"]
            else:
                l.book_num = 10

            # 2. Process fields that do affect ratings
            update_credibility = (l.credibility != list_form.cleaned_data["credibility"])
            if update_credibility:
                l.credibility = list_form.cleaned_data["credibility"]
            update_places = (l.places_matter != list_form.cleaned_data["places_matter"])      
            if update_places:
                l.places_matter = list_form.cleaned_data["places_matter"]
                if l.places_matter:
                    place = 1
                    for bil in l.book_in_list_set.all():                   
                        bil.place = place
                        bil.save()
                        place += 1
            l.save()
            # Update bil/ail + reset them             
            if update_credibility or update_places:
                set_bil_rating(list_id)
                if l.author_in_list_set.count() != 0:
                    set_ail_rating(list_id)
                     
            # Any changes to list.masters?
            current_masters_set = set(l.masters.all()) 
            new_masters = list_form.cleaned_data["masters"]
            new_masters_set = set(new_masters)
            update_masters = current_masters_set != new_masters_set
            affected_masters = new_masters_set | current_masters_set

            # If yes, then: I.Reset masters
            if update_masters:                
                l.masters.clear()
                l.masters.add(*new_masters.all()) #add masters to this list            

                """
                II.Delete bims and aims for masters from which LIST was deleted
                - Deleting bims:
                For every deleted master:
                1. Take all books in this LIST that are also in this master, 
                2. Exclude: books that are also in another list in this master, apart from the LIST
                3. Delete them
                """
                deleted_masters_set = current_masters_set - new_masters_set
                for deleted_master in deleted_masters_set:
                    values = List.objects.filter(masters=deleted_master).exclude(pk=l.id).values_list("pk", flat=True) #All lists in deleted master,except LIST
                    Book_In_Master.objects.filter(master=deleted_master, book__book_in_list__list=l).exclude(
                            book__book_in_list__list__in=list(values)
                        ).delete()
                    
                    Author_In_Master.objects.filter(author__author_in_list__list=l, master=deleted_master).exclude(
                        author__author_in_list__list__in=list(values)
                    ).delete()

                """                                                        
                III.Create bims and aims for masters in which LIST was added
                1. Take each book in this LIST, then take each master, 
                2. Then create bim in this master if it's not already there
                """
                added_masters_set = new_masters_set - current_masters_set
                for added_master in added_masters_set:
                    for book in Book.objects.filter(book_in_list__list=l): # for each book in this list
                        bim, created = Book_In_Master.objects.get_or_create(book=book, master=added_master)
                    for author in Author.objects.filter(author_in_list__list=l):
                        aim, created = Author_In_Master.objects.get_or_create(author=author, master=added_master)
                l.save()         
            # If credibility, places or masters were updated, reset bim/aim
            if update_credibility or update_places or update_masters:
                for master in affected_masters:
                    reset_bim_aim_rating(master.id)               
            messages.success(request, "Список был отредактирован")        
            return HttpResponseRedirect(reverse("list", args=(l.id, l.slug)))
    return render(request, "list/list_edit.html", {"list_form": list_form, "list": l})


@login_required
def list_delete(request, list_id):
    try:
        l = List.objects.get(pk=int(list_id))
    except:
        messages.error(request, "Такого списка не существует")
        return HttpResponseRedirect(reverse("lists"))
    if l.user != request.user:
        raise Http404
    list_masters = list(l.masters.all())
    l.delete() # bils, ails deleted automatically
    # Delete all books that aren't in any list, respective bims deleted automatically
    Book.objects.filter(book_in_list__isnull=True).delete()
    Author.objects.filter(author_in_list__isnull=True).delete()
    
    for master in list_masters:
        reset_bim_aim_rating(master.id)

        # Remove bims/aims in this master that weren't removed earlier 
        # (weren't removed because the book is in other lists and masters)
        Book_In_Master.objects.filter(rating=0).delete()
        Author_In_Master.objects.filter(rating=0).delete()
        
    messages.success(request, "Список был удален")
    return HttpResponseRedirect(reverse("lists"))


@login_required
def master_delete(request, master_id):
    try:
        master = Master.objects.get(pk=int(master_id))
    except:
        messages.error(request, "Такого МастерРэнкинга нет")
        return HttpResponseRedirect(reverse("masters"))
    if master.user != request.user:
        raise Http404
    master.delete()
    List.objects.filter(masters__isnull=True).delete()
    Book.objects.filter(book_in_list__isnull=True).delete()
    Author.objects.filter(author_in_list__isnull=True).delete()
    messages.success(request, "МастерРэнкинг был удален")
    return HttpResponseRedirect(reverse("masters"))


@csrf_exempt
@login_required
def master_edit(request, master_id):
    try:
        master = Master.objects.get(pk=int(master_id))
    except:
        return JsonResponse({"error": "МастерРэнкинг не найден"}, status=404)
    if master.user != request.user:
        raise Http404
    if request.method == "PUT":
        data = json.loads(request.body)
        if data.get("master_name") is not None:
            master.name = data["master_name"]
            master.save()
            return HttpResponse(status=204)
    return JsonResponse({"error": "PUT request required"}, status=400)


def bil_add(form, list_id, user):
    try:
        l = List.objects.get(pk=int(list_id))
    except:        
        return HttpResponseRedirect(reverse("lists"))

    book_add(form, list_id, user)

    # Reset rating for that list and for all masters this list is in
    l.book_num += 1
    l.save()
    if l.book_in_list_set.count() != 0:
        set_bil_rating(list_id)
    if l.author_in_list_set.count() != 0:
        set_ail_rating(list_id)
    if l.masters.count() != 0:
        for master in l.masters.all():
            reset_bim_aim_rating(master.id)
    return True


@login_required
def bil_edit(request, bil_id): 
    try:
        bil = Book_In_List.objects.get(pk=int(bil_id))
    except:
        messages.error(request, "Такой книги в этом списке нет")
        return HttpResponseRedirect(reverse("lists"))
    
    book = bil.book
    if book.user != request.user:
        raise Http404
    lists_containing_bil = List.objects.filter(book_in_list__book=book)

    form = BookForm(request.POST)
    if form.is_valid():
        # I. Update title, info and place(in case places matter and place changed)
        title = " ".join(form.cleaned_data["title"].split())
        try:
            book.title = title
            book.save()
        except:
            messages.error(request, "Книга под таким названием уже существует")    
            return HttpResponseRedirect(reverse("list", args=(bil.list.id, bil.list.slug))) 
        
        if form.cleaned_data["info"]:
            bil.info = form.cleaned_data["info"]
        if bil.list.places_matter and (not form.cleaned_data["place"]):
            messages.error(request, "Место книги в списке должно быть более 0")    
            return HttpResponseRedirect(reverse("list", args=(bil.list.id, bil.list.slug))) 
        bil.save()
        if bil.list.places_matter and bil.place != form.cleaned_data["place"]: 
            bil.place = form.cleaned_data["place"]
            bil.save()
            # Reset ratings only for one list and its masters
            set_bil_rating(bil.list.id)
            set_ail_rating(bil.list.id)
            for master in bil.list.masters.all():
                reset_bim_aim_rating(master.id)

        # II. Update authors
        new_authors_set = set() # All authors submitted in the form
        if form.cleaned_data["authors"]:                
            authors_str = form.cleaned_data["authors"]
            authors_list_str = authors_str.split(",")
            # Create an author. Add the author to this books if they're not already there                                           
            for name in authors_list_str:
                name = " ".join(name.split())                
                a, a_created = Author.objects.get_or_create(name=name, user=request.user)
                new_authors_set.add(a)              
        old_authors_set = set(bil.book.authors.all())     
        update_authors = (old_authors_set != new_authors_set)
        if update_authors: 
            authors_to_delete_set = old_authors_set - new_authors_set
            authors_to_add_set = new_authors_set - old_authors_set
            affected_authors_set = old_authors_set | new_authors_set
            # 1.Reset authors
            book.authors.clear()
            book.authors.add(*new_authors_set)

            if authors_to_delete_set:
                # 2. Delete ails from every list that has this book unless these authors have
                # other books in that list
                # a) take each list in which this book is present. TEST DELETE KJ
                for l in lists_containing_bil:
                    # b) take each ail in that list who is on deletion list                      
                    for ail in Author_In_List.objects.filter(list=l, author__in=authors_to_delete_set):
                        # c) if this author has only one book on this list, then delete her
                        if Book_In_List.objects.filter(list=l, book__authors=ail.author).count() == 0:
                            ail.delete()                                   

                # 3. Delete aims from every master that has this book unless these authors have. TEST DEL
                # other books in that master
                # a) take each master in which this book is present
                for master in Master.objects.filter(book_in_master__book=book):
                    # b) take each aim in that master who is in deletion list
                    for aim in Author_In_Master.objects.filter(master=master, author__in=authors_to_delete_set):                            
                        # c) if this author has only one book in this master, then delete her
                        if Book_In_Master.objects.filter(master=master, book__authors=aim.author).count() == 0:
                            aim.delete()

            if authors_to_add_set:
                # 4. Add ails/aims unless there're already ails/aims for these authors
                for author in authors_to_add_set:
                    Author_In_List.objects.get_or_create(author=author, list=bil.list)
                    for master in bil.list.masters.all():
                        Author_In_Master.objects.get_or_create(author=author, master=master)            

            # 5. Reset ails in all lists this book is in, bim_aim_ratings for all lists and masters that book is in
            for l in lists_containing_bil:                    
                set_ail_rating(l.id)

            for master in Master.objects.filter(author_in_master__author__in=affected_authors_set):
                reset_bim_aim_rating(master.id)
        messages.success(request, "Книга была отредактирована")
        return HttpResponseRedirect(reverse("list", args=(bil.list.id, bil.list.slug))) 
    messages.error(request, "Книга должна иметь название. Если список ранжированный, место книги должно быть больше 0")    
    return HttpResponseRedirect(reverse("list", args=(bil.list.id, bil.list.slug)))                          


@login_required
def bil_delete(request, bil_id):
    try:
        bil = Book_In_List.objects.get(pk=int(bil_id)) # If bil exists, list exists too
        book = Book.objects.get(book_in_list=bil)
    except:
        messages.error(request, "Такой книги нет")
        return HttpResponseRedirect(reverse("lists"))
    if book.user != request.user:
        raise Http404
    authors = book.authors.all()
    list_id = bil.list.id
    list_slug = bil.list.slug
    masters = bil.list.masters.all()

    # Delete ails unless they have other books in this list
    # a) all ails in this list who are authors of that book
    for ail in Author_In_List.objects.filter(list=bil.list, author__in=authors):
        # b) does ail have only one book in this list?
        if Book_In_List.objects.filter(list=bil.list, book__authors=ail.author).count() == 1:
            ail.delete()
        
    # Delete bims unless this book is present in other lists in this master
    for master in bil.list.masters.all():
        other_lists_in_this_master = List.objects.filter(masters=master).exclude(pk=bil.list.id).values_list("pk", flat=True)
        Book_In_Master.objects.filter(book=book, master=master).exclude(
            book__book_in_list__list__in=list(other_lists_in_this_master)).delete()
        
        # Delete aims unless this author has still ails left (that might be if 
        # this author either has another book in this list or another book in this master)
        for author in authors:
            Author_In_Master.objects.filter(author=author, master=master).exclude(
                author__author_in_list__isnull=False).delete()
    bil.list.book_num -= 1
    bil.list.save() 
    bil.delete()
    
    # Delete each author if they have not books in this list anymore or in other lists
    for author in authors:
        if author.author_in_list_set.count() == 0:
            author.delete()

    # Delete book if it isn't in any other lists
    if book.book_in_list_set.count() == 0:
       book.delete()

    # Reset rating for bils, ails in this list and all its masters
    set_bil_rating(list_id)
    set_ail_rating(list_id)
    for master in masters:
        reset_bim_aim_rating(master.id)       

    messages.success(request, "Книга была удалена из списка")
    return HttpResponseRedirect(reverse("list", args=(list_id, list_slug)))


@login_required
def books_add(request, list_id, slug):
    # book_in_list has unique constraint, author_in_list doesn't
    try:
        list, list_url = get_redirected(List, {'pk': list_id}, {'slug': slug})
        if list_url:
            return HttpResponseRedirect(list_url)
        #list = List.objects.get(pk=int(list_id))
    except:
        messages.error(request, "Такого списка нет")
        return HttpResponseRedirect(reverse("lists"))
    if list.user != request.user:
        raise Http404
    
    if request.method == "POST":
        # Create a LOOP to process every form in the formset
        if list.places_matter:
            BookFormSet = formset_factory(BookForm)
        else:
            BookFormSet = formset_factory(BookFormNoPlaces)
        formset = BookFormSet(request.POST)
        helper = BookFormSetHelper()
        if formset.is_valid():
            for form in formset:
                # Process a single form 
                if form.is_valid():
                    if form.has_changed():
                        message = book_add(form, list_id, request.user)
                        if message == "Такого списка нет":
                            messages.error(request, message)
                            return HttpResponseRedirect(reverse("lists"))
                        elif message == "Если больше 100 книг в списке имеют одинаковое название, вы можете изменить названия, чтобы избежать путаницы":
                            messages.error(request, message)    
                            return render(request, "list/books_add.html", {"formset": BookFormSet(request.POST), "helper": helper,})              
                else:
                    return render(request, "list/books_add.html", {"formset": BookFormSet(request.POST), "helper": helper,})
            '''
            Having processed all forms, we set rating for every bil, ail within this list, then reset rating for bim, aim using new data
            '''
            list.book_num = list.book_in_list_set.count()
            list.save()
            if list.book_num != 0:
                set_bil_rating(list_id)
            if list.author_in_list_set.count() != 0:
                set_ail_rating(list_id)
            if list.masters.count() != 0:
                for master in list.masters.all():
                    reset_bim_aim_rating(master.id)
            messages.success(request, "Книги были добавлены в список")
            return HttpResponseRedirect(reverse("list_done", args=(list.id, list.slug)))        
        return render(request, "list/books_add.html", {"formset": BookFormSet(request.POST), "helper": helper,})    

    # if GET request
    # "place" is pre-filled in ranked lists
    if list.places_matter:
        prepare_initial = []
        for i in range(1, list.book_num + 1): #list.book_num
            data = {"place": (i)}
            prepare_initial.append(data)
        BookFormSet = formset_factory(BookForm, extra=0)
        formset = BookFormSet(initial = prepare_initial)
        helper = BookFormSetHelper()

    else:
        BookFormSet = formset_factory(BookFormNoPlaces, extra = list.book_num)
        formset = BookFormSet()
        helper = BookFormSetHelper()

    return render(request, "list/books_add.html", {"list": list, 
                                                   "formset": formset,
                                                   "helper": helper,                                                 
                                                   })


def book_add(form, list_id, user):
    message = ""
    # Create book and author or get current ones.
    try:
        list = List.objects.get(pk=int(list_id))
    except:
        message = "Такого списка нет"
        return message
    
    if list.places_matter:
        if form.cleaned_data["place"]:
            place = form.cleaned_data["place"]
        else:
            place = 1
    else:
        place = 1

    # Check if a book with this name is present in this list
    title = " ".join(form.cleaned_data["title"].split())
    b, b_created = Book.objects.get_or_create(title=title, user=user)
    i = 1

    # Increment the additional code for the book until we reach a 'free' code -> then
    while Book_In_List.objects.filter(book=b, list=list, book__user=user).exists():
        b, b_created = Book.objects.get_or_create(title=f"{title}({i})", user=user)
        i += 1
        if i == 100:
            b.delete()
            message = "Если больше 100 книг в списке имеют одинаковое название, вы можете изменить названия, чтобы избежать путаницы"
            return message

    bil = Book_In_List.objects.create(book=b, list=list, place=place)

    if form.cleaned_data["authors"]:
        authors_str = form.cleaned_data["authors"]
        authors_list = authors_str.split(",")
        # Create an author. Add the author to this books if they're not already there                                           
        for name in authors_list:
            name = " ".join(name.split())
            a, a_created = Author.objects.get_or_create(name=name, user=user)
            if a not in b.authors.all():
                b.authors.add(a)

    # Go on creating/adding data to bil/ail/bim/aim                                    
    if form.cleaned_data["info"]:
        info = form.cleaned_data["info"]
        bil.info = info
        bil.save()
    list_masters = list.masters.all()
    for author in b.authors.all():
        ail, ail_created = Author_In_List.objects.get_or_create(author=author, list=list)

        # Create aim
        for master in list_masters: 
            aim, aim_created = Author_In_Master.objects.get_or_create(author=author, master=master)            
    # Create bim
    for master in list_masters:
        bim = Book_In_Master.objects.get_or_create(book=b, master=master)
    return message


def set_bil_rating(list_id):
    '''
    Having processed all the forms, count index for the list based on places_matter, 
    then count rating for each book in the list. 
    - count list rating ("atom_sum") now as now we know the real number of books
    - count rating of each book in list now, as the same list can be
    used in many masters, and we don't want to do the calculations again and again
    '''        
    list = List.objects.get(pk=int(list_id))
    if not list.places_matter:
        for bil in list.book_in_list_set.all():
            bil.rating = list.credibility * 10**12
            bil.save()
    else:
        '''
        Count rating of a single atom & how many atoms each book has
        Overall list_rating depends on list.credibility and how many books there're in the list
        '''
        list_max_place_dict = Book_In_List.objects.filter(list=list).aggregate(Max("place", default=0))
        list_max_place = list_max_place_dict['place__max']
        list_rating = list.credibility * 10**12 * list.book_in_list_set.count()        
        '''
        atom_count for each book reverses the book's place in the list 
        (so that top books have most rating, not vice-versa)
        '''
        list_atom_sum = 0
        for bil in list.book_in_list_set.all():
            bil.atom_count = list_max_place + 1 - bil.place
            bil.save()
            list_atom_sum += bil.atom_count
        
        # Atom_rating is the rating of every 1 in bil.place
        try:
            atom_rating = list_rating / list_atom_sum
        # If we delete last book in list, let's skip ZeroDivisionError
        except:
            HttpResponseRedirect(reverse("lists"))

        # Count rating for each book
        for bil in list.book_in_list_set.all():
            bil.rating = bil.atom_count * atom_rating
            bil.save()
    return True
    

def set_ail_rating(list_id):
    # Author ranking is the sum of rankings of all their books IN THIS LIST     
    list = List.objects.get(pk=int(list_id))
    for ail in list.author_in_list_set.all():
        rating_dict = Book_In_List.objects.filter(book__authors__author_in_list=ail, list=list).aggregate(Sum("rating"))
        ail.rating = rating_dict['rating__sum']
        ail.save()
    return True


def reset_bim_aim_rating(master_id):
    master = Master.objects.get(pk=int(master_id))
    # Count rating for every book in the master
    for bim in master.book_in_master_set.all():
        bim_rating = 0
        for bil in Book_In_List.objects.filter(list__in=master.list_set.all()):
            if bil.book == bim.book:
                bim_rating += bil.rating
        bim.rating = bim_rating // 10**11
        bim.save()
    
    bim_place_counter = 0
    bim_previous_rating = 0
    for bim in master.book_in_master_set.order_by("-rating"):
        if bim.rating != bim_previous_rating:
            bim_place_counter += 1
            bim_previous_rating = bim.rating
        bim.place = bim_place_counter
        bim.save()

    for aim in master.author_in_master_set.all():
        aim_rating = 0
        for ail in Author_In_List.objects.filter(list__in=master.list_set.all()):
            if ail.author == aim.author:
                aim_rating += ail.rating
        aim.rating = aim_rating // 10**11
        aim.save()

    aim_place_counter = 0
    aim_previous_rating = 0
    for aim in master.author_in_master_set.order_by("-rating"):
        if aim.rating != aim_previous_rating:
            aim_place_counter += 1
            aim_previous_rating = aim.rating
        aim.place = aim_place_counter
        aim.save()
    return True


@login_required
def list_done(request, list_id, slug):
    try:
        list, list_url = get_redirected(List, {'pk': list_id}, {'slug': slug})
        if list_url:
            return HttpResponseRedirect(list_url)
    except:
        messages.error(request, "Такого списка нет")
        return HttpResponseRedirect(reverse("lists"))
    if list.user != request.user:
        raise Http404
    return render(request, "list/list_done.html", {"list": list})


@login_required
def master(request, master_id, slug):    
    try:
        master, master_url = get_redirected(Master, {'pk': master_id}, {'slug': slug})
        if master_url:
            return HttpResponseRedirect(master_url)
    except:
        messages.error(request, "Такого МастерРэнкинга нет")
        return HttpResponseRedirect(reverse("masters"))
    if master.user != request.user:
        raise Http404
    return render(request, "list/master.html", {
        "master": master, 
        "books_in_master_by_rating": master.book_in_master_set.order_by("-rating"),
        "masters": Master.objects.exclude(pk=int(master_id)).all(),
        })


@login_required
def master_author_ranking(request, master_id, slug):
    try:
        master, master_url = get_redirected(Master, {'pk': master_id}, {'slug': slug})
        if master_url:
            return HttpResponseRedirect(master_url)
    except:
        messages.error(request, "Такого МастерРэнкинга нет")
        return HttpResponseRedirect(reverse("masters"))
    if master.user != request.user:
        raise Http404
    return render(request, "list/master_author_ranking.html", {
        "master": master,
        "authors_in_master_by_rating": master.author_in_master_set.order_by("-rating", "author__name"),})


@login_required
def master_lists(request, master_id, slug):
    try:
        master, master_url = get_redirected(Master, {'pk': master_id}, {'slug': slug})
        if master_url:
            return HttpResponseRedirect(master_url)
    except:
        messages.error(request, "Такого МастерРэнкинга нет")
        return HttpResponseRedirect(reverse("masters"))
    if master.user != request.user:
        raise Http404
    return render(request, "list/master_lists.html", {
        "master": master,
        "lists_in_master_by_credibility": master.list_set.order_by("-credibility", "name"),
        "form": BookForm(),
    })


@login_required
def masters(request):
    masters = Master.objects.filter(user=request.user).order_by('name')
    return render(request, "list/masters.html", {
        "masters": masters,
    })


@login_required
def lists(request):
    lists = List.objects.filter(user=request.user).order_by('name')
    return render(request, "list/lists.html", {"lists": lists,})


@login_required
def list_details(request, list_id, slug, master_id=""):
    try:
        list, list_url = get_redirected(List, {'pk': list_id}, {'slug': slug})
        if list_url:
            return HttpResponseRedirect(list_url)
        #list=List.objects.get(pk=int(list_id))
    except:
        messages.error(request, "Такого списка нет")
        return HttpResponseRedirect(reverse("lists"))
    if list.user != request.user:
        raise Http404
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            bil_add(form, list_id, request.user)
            messages.success(request, "Книга была добавлена в список")
    if master_id:
            master = Master.objects.get(pk=int(master_id))
            return HttpResponseRedirect(reverse("master_lists", args=(master.id, master.slug)))

    return render(request, "list/list.html", {"list": list, "bils_sorted": list.book_in_list_set.order_by("place", "book__title"), "form": BookForm()})


@login_required
def search(request):
    if request.method == 'POST':
        q = request.POST['q']
        masters = Master.objects.filter(name__icontains=q, user=request.user)
        lists = List.objects.filter(name__icontains=q, user=request.user)
        books = Book.objects.filter(title__icontains=q, user=request.user)
        authors = Author.objects.filter(name__icontains=q, user=request.user)
        return render(request, "list/search_results.html", {
            "masters": masters, "lists": lists, "books": books, "authors": authors, "q": q
            })
    return HttpResponseRedirect(reverse('index'))


def login_view(request):
    if request.method == "POST":
        # Attempt to sign user in
        email = request.POST["email"]
        password = request.POST["password"]
        user = authenticate(request, username=email, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            messages.success(request, "Вы вошли в систему")
            return HttpResponseRedirect(reverse("master_add"))
        else:
            messages.error(request, "Неправильный логин или пароль")
            return HttpResponseRedirect(reverse("index"))
    return HttpResponseRedirect(reverse("index"))


def logout_view(request):
    logout(request)
    messages.success(request, "Вы вышли из системы")
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]
        '''
        # Skip confirmation so that people don't lose focus and are ready
        # to understand how the project works
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            messages.error(request, "Passwords must match")
            return render(
                request, "list/register.html")
        '''
        try:
            user = User.objects.create_user(email, email, password)
            user.save()
        except IntegrityError:
            messages.error(request, "Имя пользователя занято")
            return HttpResponseRedirect(reverse("index"))
        login(request, user)
        messages.success(request, "Вы успешно зарегистрировались")
        return HttpResponseRedirect(reverse("master_add"))
    return HttpResponseRedirect(reverse("index"))
from django.shortcuts import render

def home(request):
    return render(request, 'home/index.html')

def character_creator(request):
    return render(request, 'home/character_creator.html')  # Fix this path!

Foler Breakdown: 

LOR_Website: 
Core Django elements and settings and urls config 

accounts
handle django based accounts 

campaigns(Low prio)
handles the campaign setup and attaching characters to campaign

characters 

- static
handles CSS and JS for the admin pages

- templates
holds the webpahges for it. Needs to be cleaned up

Key focus: 
create_character.html is the creation for the characters for stage 1 
character detail is the view screen 
list is to list out all characters belonging to user
level up is to control level up, might consider merging with detail

- forms.py
handle all the forms for user side 
- models.py
handles all the database definition 

- urls.py
handles the mapping

- views.py
handles webpage backend

- widgets.py
currently used as utility tools for the character setup

home
Focus is admin.py
admin.py is used to define forms in adidtion to characters file stuff. It uses it to create 
admin forms that allow the creation of classes and class features. 


venv
python virtual enviorment 




Development piorities

ensure create_character.html can submit all data. Currently certain fields are not uploaded 
to database
ensure admin can create class, class features and ensure modularity and they can be for all cases
ensure a type of class feature of feats can be connected to a google sheet
add races into admin. So stage 1 character creation can display race traits using same format as
class features. 

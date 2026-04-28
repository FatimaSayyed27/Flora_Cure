from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.utils.timezone import now
from .models import Profile , Diagnosis 
import requests
from django.contrib.auth.decorators import login_required
from .forms import ProfileForm
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io

def welcome(request):   
    return render(request, 'welcome.html')

def home(request):
    return render(request, 'home.html')

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            return render(request, "login.html", {"error": "Invalid username or password! "})
    return render(request, "login.html")

def register_view(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        # Validation — empty check
        if not full_name or not email or not password:
            return render(request, "register.html", {
                "error": "Please fill in all fields."
            })

        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # username full_name se banao
        base_username = full_name.replace(" ", "").lower()
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        Profile.objects.create(user=user)
        login(request, user)
        return redirect("home")

    return render(request, "register.html")

def dashboard_view(request):
    user = request.user

    total_diagnoses = Diagnosis.objects.filter(user=user).count()
    plants_tracked = Diagnosis.objects.filter(user=user).values("plant_name").distinct().count()
    active_treatments = Diagnosis.objects.filter(user=user, cure__icontains="Add").count()
    cured_this_month = Diagnosis.objects.filter(
        user=user,
        is_cured=True,
        date__month=now().month,
        date__year=now().year
    ).count()
    recent_diagnoses = Diagnosis.objects.filter(user=user).order_by("-date")[:5]

    context = {
        "user": user,
        "total_diagnoses": total_diagnoses,
        "plants_tracked": plants_tracked,
        "active_treatments": active_treatments,
        "cured_this_month": cured_this_month,
        "recent_diagnoses": recent_diagnoses,
    }
    return render(request, "dashboard.html", context)

def get_weather(request):
    lat = request.GET.get("lat")
    lon = request.GET.get("lon")

    if not lat or not lon:
        return JsonResponse({"error": "Location not provided"})

    api_key = "7ae268227ffad969179a8c8de6bcd22c"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"

    try:
        response = requests.get(url, timeout=10).json()

        if response.get("cod") == 200:
            temperature = round(response["main"]["temp"])
            condition = response["weather"][0]["description"].capitalize()
            city_name = response.get("name", "Your Location")

            condition_lower = condition.lower()
            if "rain" in condition_lower:
                tip = "Skip watering today — rain is expected."
            elif "clear" in condition_lower:
                tip = "Water your plants in the evening to avoid evaporation."
            elif "cloud" in condition_lower:
                tip = "Good day for watering — overcast skies help retention."
            elif "hot" in condition_lower or temperature > 35:
                tip = "Hot day! Water plants early morning or late evening."
            else:
                tip = "Check your plants and water if soil feels dry."

            return JsonResponse({
                "temperature": temperature,
                "condition": condition,
                "city": city_name,
                "tip": tip
            })
        else:
            return JsonResponse({"error": response.get("message", "Weather not found")})

    except Exception as e:
        return JsonResponse({"error": str(e)})

def get_diagnosis(symptoms):
    rules = [
        # Leaf Problems
        {
            "keywords": ["Yellowing leaves", "Yellow leaves"],
            "disease": "Nutrient Deficiency (Nitrogen)",
            "cure": "Add nitrogen-rich fertilizer like urea or compost. Check soil pH (ideal 6-7)."
        },
        {
            "keywords": ["Brown leaf tips", "Brown edges"],
            "disease": "Leaf Scorch / Salt Burn",
            "cure": "Flush soil with water to remove excess salts. Avoid over-fertilizing."
        },
        {
            "keywords": ["Black spots", "Dark spots on leaves"],
            "disease": "Fungal Leaf Spot",
            "cure": "Remove infected leaves. Apply copper-based fungicide. Avoid overhead watering."
        },
        {
            "keywords": ["White powder", "Powdery coating"],
            "disease": "Powdery Mildew",
            "cure": "Spray neem oil or baking soda solution (1 tsp per liter). Improve air circulation."
        },
        {
            "keywords": ["Rust spots", "Orange spots", "Rust colored"],
            "disease": "Rust Fungus",
            "cure": "Remove affected leaves. Apply sulfur-based fungicide. Keep foliage dry."
        },
        {
            "keywords": ["Holes in leaves", "Eaten leaves"],
            "disease": "Insect / Caterpillar Damage",
            "cure": "Apply neem oil or insecticidal soap. Handpick caterpillars if visible."
        },
        {
            "keywords": ["Curling leaves", "Leaf curl"],
            "disease": "Aphid Infestation or Heat Stress",
            "cure": "Spray strong water jet to remove aphids. Apply neem oil. Check for overheating."
        },
        {
            "keywords": ["Sticky leaves", "Sticky residue"],
            "disease": "Aphid / Whitefly Infestation",
            "cure": "Apply insecticidal soap or neem oil spray. Introduce ladybugs as natural predators."
        },
        {
            "keywords": ["Pale leaves", "Light green leaves"],
            "disease": "Chlorosis (Iron/Magnesium Deficiency)",
            "cure": "Apply iron chelate or Epsom salt (magnesium sulfate). Check soil pH."
        },
        {
            "keywords": ["Drooping leaves", "Limp leaves"],
            "disease": "Overwatering or Root Rot",
            "cure": "Reduce watering. Check drainage. Remove rotted roots and repot if needed."
        },
        # Stem Problems
        {
            "keywords": ["Wilting", "Wilted plant"],
            "disease": "Water Stress / Dehydration",
            "cure": "Water deeply and consistently. Mulch around base to retain moisture."
        },
        {
            "keywords": ["Stem rot", "Mushy stem", "Soft stem"],
            "disease": "Root/Stem Rot (Pythium or Phytophthora)",
            "cure": "Remove rotted parts. Apply fungicide. Improve soil drainage. Reduce watering."
        },
        {
            "keywords": ["Black stem", "Dark stem base"],
            "disease": "Damping Off / Blackleg Disease",
            "cure": "Remove infected plants. Improve drainage. Apply copper fungicide to soil."
        },
        {
            "keywords": ["Leggy stem", "Tall thin stem", "Stretching"],
            "disease": "Etiolation (Lack of Light)",
            "cure": "Move plant to brighter location. Provide 6-8 hours of sunlight daily."
        },
        {
            "keywords": ["Galls on stem", "Lumps on stem"],
            "disease": "Crown Gall (Bacterial)",
            "cure": "Remove and destroy infected plants. Avoid wounding plants. Sterilize tools."
        },
        # Root Problems
        {
            "keywords": ["Root rot", "Brown roots", "Smelly roots"],
            "disease": "Root Rot (Overwatering / Fungal)",
            "cure": "Remove plant from pot. Trim rotted roots. Repot in fresh dry soil. Reduce watering."
        },
        {
            "keywords": ["No growth", "Stunted growth", "Slow growth"],
            "disease": "Nutrient Deficiency or Compacted Soil",
            "cure": "Apply balanced NPK fertilizer. Loosen soil. Check for root-bound condition."
        },
        # Flower / Fruit Problems
        {
            "keywords": ["Flower drop", "Falling flowers", "Bud drop"],
            "disease": "Environmental Stress / Pollination Issue",
            "cure": "Maintain consistent temperature and humidity. Hand pollinate if needed. Avoid drafts."
        },
        {
            "keywords": ["No flowers", "Not blooming"],
            "disease": "Insufficient Light or Nutrients",
            "cure": "Increase sunlight. Apply phosphorus-rich fertilizer (bone meal). Prune old growth."
        },
        {
            "keywords": ["Fruit rot", "Rotting fruit"],
            "disease": "Blossom End Rot / Fungal Rot",
            "cure": "Add calcium to soil. Maintain consistent watering. Apply fungicide if needed."
        },
        {
            "keywords": ["Small fruit", "Underdeveloped fruit"],
            "disease": "Potassium Deficiency",
            "cure": "Apply potassium-rich fertilizer (potash). Ensure adequate pollination."
        },
        # Pest Problems
        {
            "keywords": ["Spider mites", "Fine webbing", "Tiny bugs"],
            "disease": "Spider Mite Infestation",
            "cure": "Spray neem oil or miticide. Increase humidity. Isolate infected plant."
        },
        {
            "keywords": ["Mealybugs", "White cottony mass", "White fluff"],
            "disease": "Mealybug Infestation",
            "cure": "Dab with alcohol-soaked cotton. Apply neem oil. Remove by hand."
        },
        {
            "keywords": ["Scale insects", "Brown bumps on stem"],
            "disease": "Scale Insect Infestation",
            "cure": "Scrape off scales. Apply horticultural oil. Use systemic insecticide if severe."
        },
        {
            "keywords": ["Whiteflies", "Tiny white flies", "Flying white insects"],
            "disease": "Whitefly Infestation",
            "cure": "Use yellow sticky traps. Apply neem oil or pyrethrin spray. Remove affected leaves."
        },
        {
            "keywords": ["Thrips", "Silver streaks on leaves"],
            "disease": "Thrips Infestation",
            "cure": "Apply insecticidal soap or spinosad. Remove heavily infested leaves."
        },
        # Environmental
        {
            "keywords": ["Sunburn", "Bleached leaves", "White patches"],
            "disease": "Sunscald / Sunburn",
            "cure": "Move plant to indirect light. Gradually acclimate to full sun. Water adequately."
        },
        {
            "keywords": ["Frost damage", "Cold damage", "Black after cold"],
            "disease": "Frost / Cold Injury",
            "cure": "Remove damaged tissue. Move indoors. Cover with frost cloth in cold weather."
        },
        {
            "keywords": ["Wilting despite watering", "Always wilting"],
            "disease": "Fusarium Wilt (Fungal)",
            "cure": "Remove infected plant. Solarize soil. Use resistant varieties. Apply fungicide."
        },
        {
            "keywords": ["Mosaic pattern", "Mottled leaves", "Distorted leaves"],
            "disease": "Viral Mosaic Disease",
            "cure": "No cure available. Remove infected plant immediately. Control aphids (virus vectors)."
        },
        {
            "keywords": ["Sooty mold", "Black dusty coating"],
            "disease": "Sooty Mold (Secondary Fungal)",
            "cure": "Wipe leaves with damp cloth. Control sap-sucking insects causing honeydew."
        },
    ]

    symptoms_lower = [s.lower() for s in symptoms]
    for rule in rules:
        for keyword in rule["keywords"]:
            if keyword.lower() in symptoms_lower:
                return rule["disease"], rule["cure"]

    return "Unknown Disease", "Consult a plant expert or agricultural specialist."

def diagnose_view(request):
    if request.method == "POST":
        plant_name = request.POST.get("plant_name")
        symptoms_list = request.POST.getlist("symptoms")
        symptoms = ", ".join(symptoms_list)
        plant_image = request.FILES.get("plant_image")

        if plant_name == "Other":
            plant_name = request.POST.get("plant_input")

        disease, cure = get_diagnosis(symptoms_list)

        diagnosis = Diagnosis.objects.create(
            user=request.user,
            plant_name=plant_name,
            symptoms=symptoms,
            disease=disease,
            cure=cure,
            plant_image=plant_image
        )
        return redirect("hh")

    return render(request, "diagnose.html")

def mark_cured(request, pk):
    diagnosis = get_object_or_404(Diagnosis, pk=pk, user=request.user)
    diagnosis.is_cured = True
    diagnosis.save()
    return redirect(f"/dashboard?cure={diagnosis.cure}&plant={diagnosis.plant_name}")

@login_required(login_url='/login')  # AnonymousUser fix
def profile_view(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            user.first_name = form.cleaned_data['full_name']
            user.email = form.cleaned_data['email']

            new_password = form.cleaned_data.get('new_password')
            confirm_password = form.cleaned_data.get('confirm_password')
            if new_password and new_password == confirm_password:
                user.set_password(new_password)
                update_session_auth_hash(request, user)                 

            user.save()
            form.save()

            messages.success(request, f"Profile updated successfully, {user.first_name}!")
            return redirect("profile")
    else:
        form = ProfileForm(instance=profile, initial={
            # "full_name": user.first_name or "",   # actual data dikhao
            # "email": user.email or "",
            # "city": profile.city or ""

            "full_name": "",  
            "email":"",    
            "city": ""
        })

    return render(request, "profile.html", {
        "form": form,
        "user": user   # ✅ template mein user bhejo
    })

def history_view(request):
    diagnoses = Diagnosis.objects.filter(user=request.user).order_by("-date")
    return render(request, "hh.html", {"diagnoses": diagnoses})

def hh_view(request):
    diagnoses = Diagnosis.objects.filter(user=request.user)
    return render(request, "hh.html", {"diagnoses": diagnoses})

# View Detail Page
def diagnosis_detail(request, pk):
    diagnosis = get_object_or_404(Diagnosis, pk=pk, user=request.user)
    return render(request, "diagnosis_detail.html", {"d": diagnosis})

# PDF Download
def diagnosis_pdf(request, pk):
    diagnosis = get_object_or_404(Diagnosis, pk=pk, user=request.user)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Header
    p.setFillColorRGB(0.06, 0.63, 0.35)
    p.setFont("Helvetica-Bold", 22)
    p.drawString(50, height - 60, "FloraCure — Diagnosis Report")

    # Line
    p.setStrokeColorRGB(0.06, 0.63, 0.35)
    p.line(50, height - 70, width - 50, height - 70)

    # Content
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, height - 110, f"Plant Name:")
    p.setFont("Helvetica", 13)
    p.drawString(180, height - 110, diagnosis.plant_name)

    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, height - 140, f"Disease:")
    p.setFont("Helvetica", 13)
    p.drawString(180, height - 140, diagnosis.disease)

    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, height - 170, f"Symptoms:")
    p.setFont("Helvetica", 11)
    # Long symptoms text wrap
    symptoms_text = diagnosis.symptoms
    y = height - 190
    words = symptoms_text.split(", ")
    line = ""
    for word in words:
        if len(line + word) < 70:
            line += word + ", "
        else:
            p.drawString(70, y, line)
            y -= 18
            line = word + ", "
    p.drawString(70, y, line)

    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, y - 30, f"Cure:")
    p.setFont("Helvetica", 11)
    # Cure text wrap
    cure_words = diagnosis.cure.split()
    line = ""
    y = y - 50
    for word in cure_words:
        if len(line + word) < 75:
            line += word + " "
        else:
            p.drawString(70, y, line)
            y -= 18
            line = word + " "
    p.drawString(70, y, line)

    p.setFont("Helvetica", 11)
    p.drawString(50, y - 40, f"Date: {diagnosis.date.strftime('%d %B %Y, %I:%M %p')}")

    # Footer
    p.setFillColorRGB(0.06, 0.63, 0.35)
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, 40, "Generated by FloraCure Expert System")

    p.showPage()
    p.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="FloraCure_{diagnosis.plant_name}.pdf"'
    return response

#user dikhae ga kon kon h 
# from django.contrib.auth.models import User
# User.objects.all()


#user ki detail dikhae ga 
# for u in User.objects.all():
#     print(u.username, u.email, u.password)

# User.objects.values()

# exit()


# admin ke liye h 
# http://127.0.0.1:8000/admin/
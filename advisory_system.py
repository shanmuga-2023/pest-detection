"""
Farmer-Facing Advisory System for Rice & Maize Pest & Disease Management.

Translates object detection & classification outputs into concrete, actionable agronomic
treatment recommendations (organic, chemical, dosage, preventive measures) in multiple
languages (English, Hindi, Tamil, Swahili, Spanish), and formats payloads for SMS/WhatsApp alerts.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

# Comprehensive Agronomic Knowledge Base for all 15 classes in dataset.yaml
AGRONOMIC_KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    "maize_disease_curvularia_leaf_spot": {
        "display_name": "Curvularia Leaf Spot (Maize)",
        "crop": "Maize",
        "category": "Disease (Fungal)",
        "symptoms": "Oval or circular tan lesions with red-brown borders on leaves.",
        "treatments": {
            "en": {
                "organic": "Spray Neem seed kernel extract (NSKE 5%) or Trichoderma harzianum @ 5g/L.",
                "chemical": "Spray Mancozeb 75% WP @ 2.5g/L or Carbendazim 50% WP @ 1g/L of water.",
                "dosage": "500g Mancozeb per acre diluted in 200L water.",
                "preventive": "Rotate crops with non-graminaceous species; destroy infected crop residue post-harvest."
            },
            "hi": {
                "organic": "नीम के बीज की गुठली का अर्क (NSKE 5%) या ट्राइकोडर्मा हरजिशयनम 5 ग्राम/लीटर का छिड़काव करें।",
                "chemical": "मैनकोजेब 75% WP @ 2.5g/L या कार्बेन्डाजिम 50% WP @ 1g/L पानी में मिलाकर छिड़कें।",
                "dosage": "500 ग्राम मैनकोजेब प्रति एकड़ (200 लीटर पानी)।",
                "preventive": "फसल चक्र अपनाएं और कटाई के बाद फसल अवशेष नष्ट करें।"
            },
            "ta": {
                "organic": "வேப்பங் கொட்டை சாறு (5%) அல்லது டிரைகோடர்மா ஹார்சியானம் (5 கிராம்/லிட்டர்) தெளிக்கவும்.",
                "chemical": "மேன்கோசெப் 75% WP (2.5 கிராம்/லி) அல்லது கார்பண்டாசிம் 50% WP (1 கிராம்/லி) தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 500 கிராம் மேன்கோசெப் 200 லிட்டர் நீரில் கலந்து தெளிக்கவும்.",
                "preventive": "பயிர் சுழற்சி முறை பின்பற்றவும்."
            },
            "sw": {
                "organic": "Nyunyizia dondoo ya mbegu za mwarobaini (5%) au Trichoderma harzianum.",
                "chemical": "Nyunyizia Mancozeb 75% WP @ 2.5g/L au Carbendazim 50% WP @ 1g/L.",
                "dosage": "Gramu 500 za Mancozeb kwa ekari katika lita 200 za maji.",
                "preventive": "Badilisha mazao na uchome mabaki ya mazao yaliyoathirika."
            },
            "es": {
                "organic": "Rociar extracto de semilla de neem (5%) o Trichoderma harzianum 5g/L.",
                "chemical": "Aplicar Mancozeb 75% WP (2.5g/L) o Carbendazim 50% WP (1g/L).",
                "dosage": "500g de Mancozeb por acre en 200L de agua.",
                "preventive": "Rotar cultivos y eliminar residuos de cosechas infectadas."
            }
        }
    },
    "maize_disease_maydis_leaf_blight": {
        "display_name": "Maydis Leaf Blight (Maize)",
        "crop": "Maize",
        "category": "Disease (Fungal)",
        "symptoms": "Elongated rectangular straw-colored lesions restricted by leaf veins.",
        "treatments": {
            "en": {
                "organic": "Apply bio-fungicide Pseudomonas fluorescens @ 10g/L spray.",
                "chemical": "Spray Propiconazole 25% EC @ 1ml/L or Azoxystrobin 23% SC @ 1ml/L.",
                "dosage": "200ml Propiconazole per acre in 200L water at first symptom onset.",
                "preventive": "Use resistant maize hybrids and avoid excessive nitrogen fertilizing."
            },
            "hi": {
                "organic": "स्यूडोमोनास फ्लोरेसेंस 10 ग्राम/लीटर का छिड़काव करें।",
                "chemical": "प्रोपीकोनाज़ोल 25% EC @ 1ml/L या अज़ोक्सीस्ट्रोबिन 23% SC @ 1ml/L छिड़कें।",
                "dosage": "200ml प्रोपीकोनाज़ोल प्रति एकड़ (200L पानी)।",
                "preventive": "प्रतिरोधी किस्मों का चयन करें और अत्यधिक नाइट्रोजन से बचें।"
            },
            "ta": {
                "organic": "சூடோமோனாஸ் புளோரசன்ஸ் 10 கிராம்/லிட்டர் தெளிக்கவும்.",
                "chemical": "புரோபிகோனசோல் 25% EC 1 மி.லி/லிட்டர் நீரில் கலந்து தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 200 மி.லி புரோபிகோனசோல் 200 லிட்டர் தண்ணீரில் தெளிக்கவும்.",
                "preventive": "நோய் எதிர்ப்புத் திறன் கொண்ட ரகங்களைப் பயன்படுத்தவும்."
            },
            "sw": {
                "organic": "Tumia Pseudomonas fluorescens @ 10g/L.",
                "chemical": "Nyunyizia Propiconazole 25% EC @ 1ml/L au Azoxystrobin 23% SC @ 1ml/L.",
                "dosage": "200ml za Propiconazole kwa ekari katika lita 200 za maji.",
                "preventive": "Tumia mbegu zinazohimili magonjwa."
            },
            "es": {
                "organic": "Aplicar biofungicida Pseudomonas fluorescens 10g/L.",
                "chemical": "Aplicar Propiconazol 25% EC (1ml/L) o Azoxystrobin 23% SC (1ml/L).",
                "dosage": "200ml de Propiconazol por acre en 200L de agua.",
                "preventive": "Utilizar híbridos resistentes y equilibrar la fertilización."
            }
        }
    },
    "maize_disease_sorghum_downy_mildew": {
        "display_name": "Sorghum Downy Mildew (Maize)",
        "crop": "Maize",
        "category": "Disease (Oomycete)",
        "symptoms": "Yellowish chlorotic stripes on foliage with white cottony downy growth under leaves.",
        "treatments": {
            "en": {
                "organic": "Foliar spray of Trichoderma viride culture formulation.",
                "chemical": "Seed treatment with Metalaxyl 35% WS @ 6g/kg seed; spray Metalaxyl + Mancozeb @ 2.5g/L.",
                "dosage": "500g Metalaxyl-Mancozeb combo per acre.",
                "preventive": "Ensure proper field drainage and destroy infected rogue plants immediately."
            },
            "hi": {
                "organic": "ट्राइकोडर्मा विरिडे कल्चर का पत्तों पर छिड़काव करें।",
                "chemical": "बीज उपचार में Metalaxyl 35% WS @ 6g/kg बीज; स्प्रे मेटलैक्सिल + मैनकोजेब @ 2.5g/L।",
                "dosage": "500 ग्राम मेटलैक्सिल-मैनकोजेब प्रति एकड़।",
                "preventive": "खेत में जल निकासी सही रखें और संक्रमित पौधे उखाड़कर नष्ट करें।"
            },
            "ta": {
                "organic": "ட்ரைக்கோடெர்மா விரிடி தெளிக்கவும்.",
                "chemical": "மெட்டாலாக்ஸில் + மேன்கோசெப் 2.5 கிராம்/லிட்டர் தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 500 கிராம் மெட்டாலாக்ஸில் கலவை.",
                "preventive": "பாதிக்கப்பட்ட செடிகளை பிடுங்கி அழிக்கவும்."
            },
            "sw": {
                "organic": "Nyunyizia Trichoderma viride.",
                "chemical": "Tibu mbegu kwa Metalaxyl 35% WS; nyunyizia Metalaxyl + Mancozeb @ 2.5g/L.",
                "dosage": "Gramu 500 za Metalaxyl-Mancozeb kwa ekari.",
                "preventive": "Hakikisha mifereji mizuri ya maji na ng'oa mimea iliyoathirika."
            },
            "es": {
                "organic": "Aspersión foliar con Trichoderma viride.",
                "chemical": "Tratamiento de semilla con Metalaxil 35% WS; pulverizar Metalaxil + Mancozeb (2.5g/L).",
                "dosage": "500g de combinación Metalaxil-Mancozeb por acre.",
                "preventive": "Garantizar drenaje adecuado y arrancar plantas enfermas."
            }
        }
    },
    "maize_disease_turcicum_leaf_blight": {
        "display_name": "Turcicum Leaf Blight (Maize)",
        "crop": "Maize",
        "category": "Disease (Fungal)",
        "symptoms": "Large spindle-shaped grayish-green to tan elliptical lesions.",
        "treatments": {
            "en": {
                "organic": "Spray bio-control agent Bacillus subtilis @ 5ml/L.",
                "chemical": "Foliar application of Mancozeb 75% WP @ 2.5g/L or Difenoconazole 25% EC @ 1ml/L.",
                "dosage": "500g Mancozeb in 200L water per acre at 10-14 day intervals.",
                "preventive": "Plant resistant cultivars; practice deep tillage after harvest."
            },
            "hi": {
                "organic": "बेसिलस सबटिलिस 5 मि.ली./लीटर का छिड़काव करें।",
                "chemical": "मैनकोजेब 75% WP @ 2.5g/L या डाइफेनोकोनाज़ोल 25% EC @ 1ml/L का छिड़काव करें।",
                "dosage": "500 ग्राम मैनकोजेब प्रति एकड़ (200L पानी)।",
                "preventive": "प्रतिरोधी बीज बोएं और गहरी जुताई करें।"
            },
            "ta": {
                "organic": "பசில்லஸ் சப்டிலிஸ் 5 மி.லி/லிட்டர் தெளிக்கவும்.",
                "chemical": "டிஃபெனோகோனசோல் 25% EC 1 மி.லி/லிட்டர் நீரில் கலந்து தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 200 மி.லி டிஃபெனோகோனசோல்.",
                "preventive": "ஆழ்ந்த உழவு முறை மேற்கொள்ளவும்."
            },
            "sw": {
                "organic": "Nyunyizia Bacillus subtilis @ 5ml/L.",
                "chemical": "Nyunyizia Mancozeb 75% WP @ 2.5g/L au Difenoconazole 25% EC @ 1ml/L.",
                "dosage": "Gramu 500 za Mancozeb katika lita 200 za maji kwa ekari.",
                "preventive": "Panda aina zinazohimili ugonjwa na lima kwa kina."
            },
            "es": {
                "organic": "Aplicar Bacillus subtilis (5ml/L).",
                "chemical": "Aplicar Mancozeb 75% WP (2.5g/L) o Difenoconazol 25% EC (1ml/L).",
                "dosage": "500g de Mancozeb en 200L de agua por acre.",
                "preventive": "Sembrar variedades resistentes y realizar labranza profunda."
            }
        }
    },
    "maize_pest_aphid": {
        "display_name": "Maize Leaf Aphid",
        "crop": "Maize",
        "category": "Pest (Insect)",
        "symptoms": "Clusters of small soft dark-green insects inside whorls producing sticky honeydew.",
        "treatments": {
            "en": {
                "organic": "Spray Neem oil 10,000 ppm @ 3ml/L with liquid soap; release ladybird beetles.",
                "chemical": "Spray Imidacloprid 17.8% SL @ 0.5ml/L or Thiamethoxam 25% WG @ 0.2g/L.",
                "dosage": "100ml Imidacloprid per acre dissolved in 200L water.",
                "preventive": "Avoid excessive nitrogen application; encourage natural predators."
            },
            "hi": {
                "organic": "नीम का तेल (10,000 ppm) 3 मि.ली./लीटर साबुन के साथ मिलाकर छिड़कें।",
                "chemical": "इमिडाक्लोप्रिड 17.8% SL @ 0.5ml/L या थायमेथॉक्सम 25% WG @ 0.2g/L का छिड़काव करें।",
                "dosage": "100ml इमिडाक्लोप्रिड प्रति एकड़ (200L पानी)।",
                "preventive": "संतुलित उर्वरक का प्रयोग करें और मित्र कीटों को बढ़ावा दें।"
            },
            "ta": {
                "organic": "வேப்ப எண்ணெய் 3 மி.லி/லிட்டர் ஒட்டுபசையுடன் கலந்து தெளிக்கவும்.",
                "chemical": "இமிடாக்ளோபிரிட் 17.8% SL 0.5 மி.லி/லிட்டர் தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 100 மி.லி இமிடாக்ளோபிரிட் 200 லிட்டர் நீரில் தெளிக்கவும்.",
                "preventive": "நன்மை செய்யும் பூச்சிகளை பாதுகாக்கவும்."
            },
            "sw": {
                "organic": "Nyunyizia mafuta ya mwarobaini 3ml/L na sabuni; release ladybird beetles.",
                "chemical": "Nyunyizia Imidacloprid 17.8% SL @ 0.5ml/L au Thiamethoxam 25% WG @ 0.2g/L.",
                "dosage": "100ml za Imidacloprid kwa ekari katika lita 200 za maji.",
                "preventive": "Epuka matumizi yaliyopitiliza ya mbolea ya Nitrojeni."
            },
            "es": {
                "organic": "Rociar aceite de neem (3ml/L) con jabón; liberar mariquitas depredadoras.",
                "chemical": "Aplicar Imidacloprid 17.8% SL (0.5ml/L) o Tiametoxam 25% WG (0.2g/L).",
                "dosage": "100ml de Imidacloprid por acre en 200L de agua.",
                "preventive": "Evitar exceso de nitrógeno y favorecer la fauna auxiliar."
            }
        }
    },
    "maize_pest_fall_armyworm": {
        "display_name": "Fall Armyworm (FAW)",
        "crop": "Maize",
        "category": "Pest (Insect)",
        "symptoms": "Ragged hole feeding on leaves, sawdust-like frass inside whorls, inverted Y on larva head.",
        "treatments": {
            "en": {
                "organic": "Apply Metarhizium anisopliae or Bacillus thuringiensis (Bt) @ 2g/L; sand/ash in whorls.",
                "chemical": "Spray Emamectin benzoate 5% SG @ 0.4g/L or Spinetoram 11.7% SC @ 0.5ml/L directly into whorls.",
                "dosage": "80g Emamectin Benzoate or 100ml Spinetoram per acre in early morning/evening.",
                "preventive": "Install FAW pheromone traps (4-5 traps/acre) for early monitoring."
            },
            "hi": {
                "organic": "बेसिलस थुरिंजिएंसिस (Bt) 2g/L छिड़कें या पोंगियों में सूखी रेत/राख डालें।",
                "chemical": "इमामेक्टिन बेंजोएट 5% SG @ 0.4g/L या स्पिनेटोरम 11.7% SC @ 0.5ml/L पोंगी में छिड़कें।",
                "dosage": "80 ग्राम इमामेक्टिन बेंजोएट प्रति एकड़ (200L पानी)।",
                "preventive": "शुरुआती निगरानी के लिए फेरोमोन प्रपंच (4-5 ट्रैप/एकड़) लगाएं।"
            },
            "ta": {
                "organic": "பேசில்லஸ் துரிஞ்சியென்சிஸ் 2 கிராம்/லிட்டர் அல்லது சுழல் பகுதியில் மணல்/சாம்பல் இடவும்.",
                "chemical": "எமாமெக்டின் பென்சோயேட் 5% SG 0.4 கிராம்/லிட்டர் தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 80 கிராம் எமாமெக்டின் பென்சோயேட் 200 லிட்டர் நீரில்.",
                "preventive": "இனக்கவர்ச்சி பொறிகளை அமைக்கவும்."
            },
            "sw": {
                "organic": "Weka sand/jivu kwenye majani au nyunyizia Bacillus thuringiensis (Bt) @ 2g/L.",
                "chemical": "Nyunyizia Emamectin benzoate 5% SG @ 0.4g/L au Spinetoram 11.7% SC @ 0.5ml/L.",
                "dosage": "Gramu 80 za Emamectin Benzoate kwa ekari.",
                "preventive": "Weka mitego ya pheromone 4-5 kwa ekari."
            },
            "es": {
                "organic": "Aplicar Bacillus thuringiensis (Bt) 2g/L o colocar ceniza/arena en el cogollo.",
                "chemical": "Aplicar Emamectina benzoato 5% SG (0.4g/L) o Espinetoram 11.7% SC (0.5ml/L) al cogollo.",
                "dosage": "80g de Emamectina Benzoato por acre en 200L de agua.",
                "preventive": "Instalar trampas de feromonas (4-5 por acre) para monitoreo temprano."
            }
        }
    },
    "maize_pest_faw_symptoms": {
        "display_name": "Fall Armyworm Damage Symptoms",
        "crop": "Maize",
        "category": "Pest Symptoms",
        "symptoms": "Severe foliar windowing, shot-hole perforations, damaged growing points.",
        "treatments": {
            "en": {
                "organic": "Apply 5% Neem Seed Kernel Extract inside leaf whorls; release Trichogramma egg parasitoids.",
                "chemical": "Targeted application of Chlorantraniliprole 18.5% SC @ 0.4ml/L into whorl cavity.",
                "dosage": "60ml Chlorantraniliprole per acre diluted in 200L water.",
                "preventive": "Conduct regular scoutings twice weekly; destroy egg masses manually."
            },
            "hi": {
                "organic": "नीम खली अर्क 5% पोंगी में डालें; ट्राइकोग्रामा परजीवी छोड़ें।",
                "chemical": "क्लोरांट्रानिलिप्रोल 18.5% SC @ 0.4ml/L का पोंगी में प्रयोग करें।",
                "dosage": "60ml क्लोरांट्रानिलिप्रोल प्रति एकड़ (200L पानी)।",
                "preventive": "सप्ताह में दो बार खेत का निरीक्षण करें और अंडों को नष्ट करें।"
            },
            "ta": {
                "organic": "5% வேப்பங் கொட்டை சாறு சுழலில் இடவும்.",
                "chemical": "குளோரான்ட்ரானிலிப்ரோல் 18.5% SC 0.4 மி.லி/லிட்டர் சுழலில் தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 60 மி.லி குளோரான்ட்ரானிலிப்ரோல்.",
                "preventive": "வாரத்திற்கு இருமுறை வயலை கண்காணிக்கவும்."
            },
            "sw": {
                "organic": "Weka dondoo ya mwarobaini 5% kwenye kichanja cha majani.",
                "chemical": "Nyunyizia Chlorantraniliprole 18.5% SC @ 0.4ml/L.",
                "dosage": "60ml za Chlorantraniliprole kwa ekari.",
                "preventive": "Kagua shamba mara mbili kwa wiki na uharibu mayai."
            },
            "es": {
                "organic": "Aplicar extracto de neem al 5% en el cogollo y liberar avispas Trichogramma.",
                "chemical": "Aplicar Clorantraniliprol 18.5% SC (0.4ml/L) al interior del cogollo.",
                "dosage": "60ml de Clorantraniliprol por acre en 200L de agua.",
                "preventive": "Inspeccionar el cultivo 2 veces por semana y destruir masas de huevos."
            }
        }
    },
    "rice_disease_bacterial_leaf_blight": {
        "display_name": "Bacterial Leaf Blight (Rice)",
        "crop": "Rice",
        "category": "Disease (Bacterial)",
        "symptoms": "Wavy yellowish-orange lesions starting from leaf tips drying into bleached straw margins.",
        "treatments": {
            "en": {
                "organic": "Spray Fresh Cow Dung extract (20%) settled supernatant or Pseudomonas fluorescens @ 10g/L.",
                "chemical": "Spray Streptocycline @ 0.1g/L + Copper Oxychloride 50% WP @ 2.5g/L.",
                "dosage": "15g Streptocycline + 500g Copper Oxychloride per acre in 200L water.",
                "preventive": "Drain excess water from field; avoid clipping leaf tips during transplanting."
            },
            "hi": {
                "organic": "स्यूडोमोनास फ्लोरेसेंस 10 ग्राम/लीटर या ताजे गोबर का घोल (20%) छिड़कें।",
                "chemical": "स्ट्रैप्टोसाइक्लिन @ 0.1g/L + कॉपर ऑक्सीक्लोराइड 50% WP @ 2.5g/L का घोल बनाएं।",
                "dosage": "15 ग्राम स्ट्रैप्टोसाइक्लिन + 500 ग्राम कॉपर ऑक्सीक्लोराइड प्रति एकड़।",
                "preventive": "खेत से अतिरिक्त पानी निकाल दें और रोपाई के समय पत्तियों की नोक न काटें।"
            },
            "ta": {
                "organic": "சூடோமோனாஸ் புளோரசன்ஸ் 10 கிராம்/லிட்டர் தெளிக்கவும்.",
                "chemical": "ஸ்ட்ரெப்டோமைசின் (0.1 கிராம்/லி) + காப்பர் ஆக்சிகுளோரைடு (2.5 கிராம்/லி) தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 15 கிராம் ஸ்ட்ரெப்டோமைசின் + 500 கிராம் காப்பர் ஆக்சிகுளோரைடு.",
                "preventive": "வயலில் அதிகப்படியான நீரை வடித்து விடவும்."
            },
            "sw": {
                "organic": "Nyunyizia Pseudomonas fluorescens @ 10g/L au samadi safi ya ng'ombe iliyochujwa.",
                "chemical": "Nyunyizia Streptocycline @ 0.1g/L + Copper Oxychloride 50% WP @ 2.5g/L.",
                "dosage": "15g za Streptocycline + 500g za Copper Oxychloride kwa ekari.",
                "preventive": "Punguza maji yaliyokithiri shambani."
            },
            "es": {
                "organic": "Aplicar Pseudomonas fluorescens (10g/L) o bio-extractos bactericidas.",
                "chemical": "Mezclar Estreptomicina (0.1g/L) + Oxicloruro de Cobre 50% WP (2.5g/L).",
                "dosage": "15g de Estreptomicina + 500g de Oxicloruro de Cobre por acre.",
                "preventive": "Drenar el agua estancada y evitar daños mecánicos en el trasplante."
            }
        }
    },
    "rice_disease_brown_spot": {
        "display_name": "Brown Spot (Rice)",
        "crop": "Rice",
        "category": "Disease (Fungal)",
        "symptoms": "Oval sesame-seed sized brown spots with yellow halos spread across leaf blades.",
        "treatments": {
            "en": {
                "organic": "Soil application of Neem cake @ 100kg/acre; spray Vermicompost tea.",
                "chemical": "Spray Edifenphos 50% EC @ 1ml/L or Mancozeb 75% WP @ 2.5g/L.",
                "dosage": "500g Mancozeb per acre; ensure adequate Potash fertilizing.",
                "preventive": "Correct soil nutrient deficiencies (Potassium & Silicon); treat seeds before sowing."
            },
            "hi": {
                "organic": "नीम की खली (100 किग्रा/एकड़) डालें; वर्मीकंपोस्ट टी का छिड़काव करें।",
                "chemical": "एडीफेनफॉस 50% EC @ 1ml/L या मैनकोजेब 75% WP @ 2.5g/L छिड़कें।",
                "dosage": "500 ग्राम मैनकोजेब प्रति एकड़; पोटेशियम उर्वरक पर्याप्त मात्रा में दें।",
                "preventive": "मिट्टी में पोटाश की कमी पूरी करें और बीज उपचार करें।"
            },
            "ta": {
                "organic": "வேப்பம் பிண்ணாக்கு ஏக்கருக்கு 100 கிலோ இடவும்.",
                "chemical": "மேன்கோசெப் 75% WP 2.5 கிராம்/லிட்டர் தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 500 கிராம் மேன்கோசெப்; பொட்டாஷ் உரம் சரியாக இடவும்.",
                "preventive": "பொட்டாசியம் சத்து குறைபாட்டை சரி செய்யவும்."
            },
            "sw": {
                "organic": "Weka keki ya mwarobaini 100kg kwa ekari au chai ya vermicompost.",
                "chemical": "Nyunyizia Edifenphos 50% EC @ 1ml/L au Mancozeb 75% WP @ 2.5g/L.",
                "dosage": "Gramu 500 za Mancozeb kwa ekari.",
                "preventive": "Rekebisha ukosefu wa virutubisho vya potasiamu na silicon."
            },
            "es": {
                "organic": "Aplicar torta de neem (100kg/acre) e infusiones de vermicompost.",
                "chemical": "Rociar Edifenphos 50% EC (1ml/L) o Mancozeb 75% WP (2.5g/L).",
                "dosage": "500g de Mancozeb por acre; complementar fertilización con Potasio.",
                "preventive": "Corregir deficiencias de potasio en suelo y desinfectar semillas."
            }
        }
    },
    "rice_disease_false_smut": {
        "display_name": "False Smut (Rice)",
        "crop": "Rice",
        "category": "Disease (Fungal)",
        "symptoms": "Individual rice grains transformed into velvety orange/yellow pulverulent balls turning dark green.",
        "treatments": {
            "en": {
                "organic": "Foliar application of Copper Hydroxide bio-formulation at booting stage.",
                "chemical": "Spray Copper Oxychloride 50% WP @ 2.5g/L or Tebuconazole 50% + Trifloxystrobin 25% WG @ 0.4g/L.",
                "dosage": "80g Tebuconazole combo per acre applied strictly at panicle emergence stage.",
                "preventive": "Avoid excessive nitrogen application at flowering; destroy infected panicles."
            },
            "hi": {
                "organic": "बालियां निकलने की अवस्था पर कॉपर हाइड्रोक्साइड का छिड़काव करें।",
                "chemical": "कॉपर ऑक्सीक्लोराइड @ 2.5g/L या टेबुकोनाज़ोल + ट्राइफ्लॉक्सीस्ट्रोबिन @ 0.4g/L छिड़कें।",
                "dosage": "80 ग्राम टेबुकोनाज़ोल कॉम्बिनेशन प्रति एकड़।",
                "preventive": "फूल आने के समय अधिक नाइट्रोजन न दें और प्रभावित बालियां नष्ट करें।"
            },
            "ta": {
                "organic": "காப்பர் ஹைட்ராக்சைடு தெளிக்கவும்.",
                "chemical": "டெபுகோனசோல் + ட்ரைஃப்ளோக்சிஸ்ட்ரோபின் 0.4 கிராம்/லிட்டர் தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 80 கிராம் பூஞ்சானக்கொல்லி கலவை.",
                "preventive": "பூக்கும் தருணத்தில் அதிக நைட்ரஜன் உரம் இட வேண்டாம்."
            },
            "sw": {
                "organic": "Nyunyizia Copper Hydroxide wakati wa kutoka kwa mimba ya mpunga.",
                "chemical": "Nyunyizia Copper Oxychloride @ 2.5g/L au Tebuconazole + Trifloxystrobin @ 0.4g/L.",
                "dosage": "Gramu 80 za Tebuconazole combo kwa ekari.",
                "preventive": "Epuka nitrojeni iliyopitiliza na uchome mashada yaliyoathirika."
            },
            "es": {
                "organic": "Aplicar fungicida a base de Hidróxido de Cobre antes de la floración.",
                "chemical": "Pulverizar Oxicloruro de Cobre (2.5g/L) o Tebuconazol + Trifloxistrobina (0.4g/L).",
                "dosage": "80g de combinación Tebuconazol por acre en fase de embuche.",
                "preventive": "Evitar exceso de nitrógeno durante la floración y destruir espigas afectadas."
            }
        }
    },
    "rice_disease_leaf_sheath_blight": {
        "display_name": "Sheath Blight (Rice)",
        "crop": "Rice",
        "category": "Disease (Fungal)",
        "symptoms": "Oval greenish-gray spots with reddish-brown margins on leaf sheaths near waterline.",
        "treatments": {
            "en": {
                "organic": "Soil incorporation of Trichoderma harzianum @ 2.5kg/acre with FYM.",
                "chemical": "Spray Hexaconazole 5% EC @ 2ml/L or Validamycin 3% L @ 2ml/L.",
                "dosage": "400ml Hexaconazole per acre thoroughly targeted at base of tillers.",
                "preventive": "Maintain optimum plant spacing; drain field water for 3-4 days mid-season."
            },
            "hi": {
                "organic": "ट्राइकोडर्मा हरजिशयनम (2.5 किग्रा/एकड़) गोबर की खाद के साथ मिलाएं।",
                "chemical": "हेक्साकोनाज़ोल 5% EC @ 2ml/L या वैलिडामाइसिन 3% L @ 2ml/L का छिड़काव करें।",
                "dosage": "400ml हेक्साकोनाज़ोल प्रति एकड़ (पौधों की जड़ों/तनों पर केंद्रित)।",
                "preventive": "पौधों के बीच उचित दूरी रखें और बीच में 3-4 दिन पानी सुखाएं।"
            },
            "ta": {
                "organic": "ட்ரைக்கோடெர்மா ஹார்சியானம் 2.5 கிலோ/ஏக்கர் இடவும்.",
                "chemical": "ஹெக்ஸாகோனசோல் 5% EC 2 மி.லி/லிட்டர் தண்டுப் பகுதியில் தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 400 மி.லி ஹெக்ஸாகோனசோல்.",
                "preventive": "பயிர்களுக்கு இடையே போதுமான இடைவெளி வைக்கவும்."
            },
            "sw": {
                "organic": "Weka Trichoderma harzianum @ 2.5kg/ekari kwenye samadi.",
                "chemical": "Nyunyizia Hexaconazole 5% EC @ 2ml/L au Validamycin 3% L @ 2ml/L.",
                "dosage": "400ml za Hexaconazole kwa ekari kwenye shina la mpunga.",
                "preventive": "Zingatia nafasi sahihi ya kupanda na kausha maji kwa siku 3-4."
            },
            "es": {
                "organic": "Incorporar Trichoderma harzianum (2.5kg/acre) mezclado con estiércol compostado.",
                "chemical": "Aplicar Hexaconazol 5% EC (2ml/L) o Validamicina 3% L (2ml/L) al tallo.",
                "dosage": "400ml de Hexaconazol por acre directo a la base de la macolla.",
                "preventive": "Respetar distancias de siembra y secar el terreno 3 días a mitad del ciclo."
            }
        }
    },
    "rice_pest_leaf_folder": {
        "display_name": "Rice Leaf Folder",
        "crop": "Rice",
        "category": "Pest (Insect)",
        "symptoms": "Leaves folded longitudinally with silk threads; white transparent longitudinal streaks.",
        "treatments": {
            "en": {
                "organic": "Pass a long thorny bush or rope across crop canopy to open folded leaves; release Trichogramma chilonis.",
                "chemical": "Spray Cartap Hydrochloride 50% SP @ 2g/L or Chlorantraniliprole 18.5% SC @ 0.3ml/L.",
                "dosage": "60ml Chlorantraniliprole or 400g Cartap per acre diluted in 200L water.",
                "preventive": "Avoid excessive nitrogenous fertilizer application; keep field bunds weed-free."
            },
            "hi": {
                "organic": "पत्तियों को खोलने के लिए खेत में रस्सी खींचें; ट्राइकोग्रामा काइलोनिस छोड़ें।",
                "chemical": "कार्टाप हाइड्रोक्लोराइड 50% SP @ 2g/L या क्लोरांट्रानिलिप्रोल @ 0.3ml/L छिड़कें।",
                "dosage": "60ml क्लोरांट्रानिलिप्रोल या 400 ग्राम कार्टाप प्रति एकड़।",
                "preventive": "यूरिया का अत्यधिक प्रयोग न करें और मेड़ों की सफाई रखें।"
            },
            "ta": {
                "organic": "மடிந்த இலைகளை பிரிக்க கயிறு இழுத்தல் முறை மேற்கொள்ளவும்.",
                "chemical": "கார்ட்டாப் ஹைட்ரோகுளோரைடு 50% SP 2 கிராம்/லிட்டர் தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 400 கிராம் கார்ட்டாப் 200 லிட்டர் நீரில்.",
                "preventive": "அதிக நைட்ரஜன் உரம் இட வேண்டாம்."
            },
            "sw": {
                "organic": "Vuta kamba juu ya majani yaliyokunjwa; release Trichogramma chilonis.",
                "chemical": "Nyunyizia Cartap Hydrochloride 50% SP @ 2g/L au Chlorantraniliprole @ 0.3ml/L.",
                "dosage": "60ml za Chlorantraniliprole au 400g za Cartap kwa ekari.",
                "preventive": "Epuka mbolea iliyopitiliza ya nitrojeni na safisha magugu."
            },
            "es": {
                "organic": "Pasar una cuerda sobre el cultivo para desenrollar hojas; liberar Trichogramma chilonis.",
                "chemical": "Aplicar Cartap Hidrocloruro 50% SP (2g/L) o Clorantraniliprol (0.3ml/L).",
                "dosage": "60ml de Clorantraniliprol o 400g de Cartap por acre.",
                "preventive": "Evitar exceso de urea y mantener los bordes del lote limpios."
            }
        }
    },
    "rice_pest_rice_skipper": {
        "display_name": "Rice Skipper Butterfly Caterpillar",
        "crop": "Rice",
        "category": "Pest (Insect)",
        "symptoms": "Edges of leaves rolled and fastened together with silk tube; defoliation along leaf blade.",
        "treatments": {
            "en": {
                "organic": "Handpick and destroy leaf rolls; spray Beauveria bassiana @ 5g/L.",
                "chemical": "Spray Chlorpyrifos 20% EC @ 2ml/L or Quinalphos 25% EC @ 2ml/L.",
                "dosage": "400ml Chlorpyrifos per acre diluted in 200L water.",
                "preventive": "Scout field edges during vegetative growth phase; encourage insectivorous birds."
            },
            "hi": {
                "organic": "पत्ती के मोड़ों को हाथ से इकट्ठा करके नष्ट करें; ब्यूवेरिया बेसियाना 5g/L छिड़कें।",
                "chemical": "क्लोरपायरीफॉस 20% EC @ 2ml/L या क्विनाल्फॉस 25% EC @ 2ml/L का छिड़काव करें।",
                "dosage": "400ml क्लोरपायरीफॉस प्रति एकड़ (200L पानी)।",
                "preventive": "वानस्पतिक वृद्धि के समय खेत की निगरानी करें और पक्षियों के बैठने के अड्डे बनाएं।"
            },
            "ta": {
                "organic": "சுருட்டிய இலைகளை சேகரித்து அழிக்கவும்; பியூவேரியா பாசியானா 5 கிராம்/லிட்டர் தெளிக்கவும்.",
                "chemical": "குயினால்பாஸ் 25% EC 2 மி.லி/லிட்டர் தெளிக்கவும்.",
                "dosage": "ஏக்கருக்கு 400 மி.லி குயினால்பாஸ் 200 லிட்டர் தண்ணீரில்.",
                "preventive": "பறவை தாங்கிகளை வயலில் அமைக்கவும்."
            },
            "sw": {
                "organic": "Okota na uharibu majani yaliyokunjwa; nyunyizia Beauveria bassiana @ 5g/L.",
                "chemical": "Nyunyizia Chlorpyrifos 20% EC @ 2ml/L au Quinalphos 25% EC @ 2ml/L.",
                "dosage": "400ml za Chlorpyrifos kwa ekari katika lita 200 za maji.",
                "preventive": "Weka sehemu za ndege kutua Shambani."
            },
            "es": {
                "organic": "Recolectar y destruir rollos de hojas; aplicar Beauveria bassiana (5g/L).",
                "chemical": "Rociar Clorpirifos 20% EC (2ml/L) o Quinalfos 25% EC (2ml/L).",
                "dosage": "400ml de Clorpirifos por acre en 200L de agua.",
                "preventive": "Instalar perchas para aves insectívoras en el lote."
            }
        }
    },
    "rice_pest_white_stem_borer": {
        "display_name": "White Stem Borer (Rice)",
        "crop": "Rice",
        "category": "Pest (Insect)",
        "symptoms": "Dead hearts in vegetative stage; empty erect white panicles (whiteheads) at reproductive stage.",
        "treatments": {
            "en": {
                "organic": "Install light traps (1 trap/acre); clipping leaf tips of seedlings before transplanting to remove egg masses.",
                "chemical": "Apply Carbofuran 3% G @ 10kg/acre or Fipronil 0.3% G @ 7.5kg/acre standing water.",
                "dosage": "7.5kg Fipronil granules per acre broadcasted in 2-3 inches standing water.",
                "preventive": "Harvest at ground level; submerge stubbles after harvest."
            },
            "hi": {
                "organic": "प्रकाश प्रपंच (1 ट्रैप/एकड़) लगाएं; रोपाई से पहले पौध की नोक काटें।",
                "chemical": "फिप्रोनिल 0.3% G @ 7.5kg/एकड़ या कार्बोफ्यूरॉन 3% G @ 10kg/एकड़ पानी में छिड़कें।",
                "dosage": "7.5 किग्रा फिप्रोनिल दानेदार प्रति एकड़ खड़े पानी में।",
                "preventive": "फसल की कटाई जमीन के समतल से करें और अवशेषों को पानी में डुबाएं।"
            },
            "ta": {
                "organic": "ஒளிப் பொறிகளை அமைத்து தாய் அந்துப்பூச்சிகளை அழிக்கவும்.",
                "chemical": "பிப்ரோனில் 0.3% G ஏக்கருக்கு 7.5 கிலோ தேங்கி நிற்கும் நீரில் இடவும்.",
                "dosage": "ஏக்கருக்கு 7.5 கிலோ பிப்ரோனில் குருணை உரம்.",
                "preventive": "தரை மட்டத்திற்கு பயிர் அறுவடை செய்யவும்."
            },
            "sw": {
                "organic": "Weka mitego ya mwanga (1 trap/ekari); kata ncha za majani kabla ya kupanda.",
                "chemical": "Weka granule za Fipronil 0.3% G @ 7.5kg/ekari kwenye maji yaliyotuama.",
                "dosage": "7.5kg za Fipronil granules kwa ekari.",
                "preventive": "Vuna karibu kabisa na udongo na tumbukiza visiki majini."
            },
            "es": {
                "organic": "Instalar trampas de luz (1/acre); cortar puntas de plántulas antes del trasplante.",
                "chemical": "Aplicar Fipronil 0.3% G (7.5kg/acre) o Carbofurán 3% G en agua estancada.",
                "dosage": "7.5kg de Fipronil granular al voleo en agua estancada.",
                "preventive": "Cosechar a ras del suelo e inundar los rastrojos post-cosecha."
            }
        }
    },
    "rice_pest_yellow_stem_borer": {
        "display_name": "Yellow Stem Borer (Rice)",
        "crop": "Rice",
        "category": "Pest (Insect)",
        "symptoms": "Yellowish-brown larvae inside stems causing 'dead hearts' and unfilled 'whiteheads'.",
        "treatments": {
            "en": {
                "organic": "Release egg parasitoid Trichogramma japonicum @ 40,000/acre at weekly intervals.",
                "chemical": "Broadcast Cartap Hydrochloride 4% G @ 8kg/acre or Chlorantraniliprole 0.4% G @ 4kg/acre.",
                "dosage": "4kg Chlorantraniliprole granules per acre mixed with dry sand.",
                "preventive": "Avoid late transplanting; clip seedling tips to destroy egg masses."
            },
            "hi": {
                "organic": "ट्राइकोग्रामा जैपोनिकम परजीवी (40,000/एकड़) का साप्ताहिक छिड़काव करें।",
                "chemical": "क्लोरांट्रानिलिप्रोल 0.4% G @ 4kg/एकड़ या कार्टाप 4% G @ 8kg/एकड़ का भुरकाव करें।",
                "dosage": "4 किग्रा क्लोरांट्रानिलिप्रोल दानेदार प्रति एकड़।",
                "preventive": "देर से रोपाई न करें और नर्सरी में पौध की नोक काटें।"
            },
            "ta": {
                "organic": "ட்ரைக்கோடெர்மா ஜபோனிகம் முட்டை ஒட்டுண்ணிகளை ஏக்கருக்கு 40,000 வெளியிடவும்.",
                "chemical": "குளோரான்ட்ரானிலிப்ரோல் 0.4% G ஏக்கருக்கு 4 கிலோ இடவும்.",
                "dosage": "ஏக்கருக்கு 4 கிலோ குருணை உரம்.",
                "preventive": "தாமதமாக நறுவு செய்வதை தவிர்க்கவும்."
            },
            "sw": {
                "organic": "Weka Trichogramma japonicum @ 40,000/ekari kila wiki.",
                "chemical": "Weka Cartap Hydrochloride 4% G @ 8kg/ekari au Chlorantraniliprole 0.4% G @ 4kg/ekari.",
                "dosage": "4kg za Chlorantraniliprole granules kwa ekari.",
                "preventive": "Epuka kuchelewa kupanda na kata ncha za miche."
            },
            "es": {
                "organic": "Liberar Trichogramma japonicum (40,000/acre) cada semana.",
                "chemical": "Aplicar Cartap Hidrocloruro 4% G (8kg/acre) o Clorantraniliprol 0.4% G (4kg/acre).",
                "dosage": "4kg de Clorantraniliprol granular por acre.",
                "preventive": "Evitar trasplante tardío y despuntar plántulas en semillero."
            }
        }
    }
}


def get_treatment_advisory(class_name: str, lang: str = "en") -> Dict[str, Any]:
    """Retrieve full treatment advisory for a given target detection class and language."""
    kb = AGRONOMIC_KNOWLEDGE_BASE.get(class_name)
    if not kb:
        return {
            "class_name": class_name,
            "display_name": class_name.replace("_", " ").title(),
            "crop": "Unknown",
            "category": "General Target",
            "symptoms": "Visual anomaly detected on foliage.",
            "treatment": {
                "organic": "Inspect field closely and isolate affected plants.",
                "chemical": "Consult local agricultural extension officer for specific pesticide selection.",
                "dosage": "Follow standard label instructions.",
                "preventive": "Maintain field hygiene and balanced irrigation."
            }
        }

    lang_code = lang.lower() if lang.lower() in kb["treatments"] else "en"
    treatment = kb["treatments"].get(lang_code, kb["treatments"]["en"])

    return {
        "class_name": class_name,
        "display_name": kb["display_name"],
        "crop": kb["crop"],
        "category": kb["category"],
        "symptoms": kb["symptoms"],
        "treatment": treatment,
        "language": lang_code
    }


def generate_sms_alert(detections: List[Dict[str, Any]], farmer_name: str = "Farmer", lang: str = "en") -> str:
    """Format a clean SMS text message summarizing the detected pests/diseases and immediate remedy."""
    if not detections:
        return f"🌾 AgriAI Alert for {farmer_name}: Field scan complete. No severe pests or diseases detected! Keep up good management."

    top = detections[0]
    cls_name = top.get("class", top.get("name", "pest_disease"))
    conf = top.get("confidence", top.get("conf", 0.90))
    adv = get_treatment_advisory(cls_name, lang=lang)

    treat = adv["treatment"]
    if lang == "hi":
        msg = (
            f"🌾 AgriAI कृषि चेतावनी ({farmer_name}):\n"
            f"पहचान: {adv['display_name']} (सटीकता: {conf*100:.1f}%)\n"
            f"जैविक इलाज: {treat['organic']}\n"
            f"रासायनिक इलाज: {treat['chemical']}\n"
            f"खुराक: {treat['dosage']}"
        )
    elif lang == "ta":
        msg = (
            f"🌾 AgriAI விவசாய எச்சரிக்கை ({farmer_name}):\n"
            f"கண்டறியப்பட்டது: {adv['display_name']} ({conf*100:.1f}%)\n"
            f"இயற்கை மருத்துவம்: {treat['organic']}\n"
            f"ரசாயன மருந்து: {treat['chemical']}\n"
            f"அளவு: {treat['dosage']}"
        )
    else:
        msg = (
            f"🌾 AgriAI Crop Alert for {farmer_name}:\n"
            f"Detected: {adv['display_name']} ({conf*100:.1f}% confidence)\n"
            f"• Organic Action: {treat['organic']}\n"
            f"• Chemical Remedy: {treat['chemical']}\n"
            f"• Dosage: {treat['dosage']}"
        )
    return msg


def generate_whatsapp_payload(detections: List[Dict[str, Any]], phone_number: str = "+919876543210", lang: str = "en") -> Dict[str, Any]:
    """Generate structured WhatsApp API JSON payload (Meta Business / Twilio API compatible)."""
    if not detections:
        body = "🌾 *AgriAI Field Monitoring Report*\n\n✅ No pest or disease symptoms detected. Crop health is optimal!"
    else:
        top = detections[0]
        cls_name = top.get("class", top.get("name", "pest_disease"))
        conf = top.get("confidence", top.get("conf", 0.90))
        adv = get_treatment_advisory(cls_name, lang=lang)
        treat = adv["treatment"]

        body = (
            f"🌾 *AgriAI Crop Health Warning*\n\n"
            f"🚨 *Target*: {adv['display_name']}\n"
            f"📊 *Confidence*: {conf*100:.1f}%\n"
            f"🌱 *Crop*: {adv['crop']} | *Category*: {adv['category']}\n\n"
            f"🔍 *Symptoms*: {adv['symptoms']}\n\n"
            f"💡 *Organic Remedy*:\n{treat['organic']}\n\n"
            f"🧪 *Chemical Treatment*:\n{treat['chemical']}\n\n"
            f"⚖️ *Dosage & Application*:\n{treat['dosage']}\n\n"
            f"🛡️ *Preventive Measures*:\n{treat['preventive']}"
        )

    return {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": body}
    }


def agribot_query_handler(query: str, last_detection: str | None = None, lang: str = "en") -> str:
    """Interactive Multilingual AgriBot response generator for farmer queries."""
    q = query.lower()

    if not last_detection:
        last_detection = "rice_pest_yellow_stem_borer"

    adv = get_treatment_advisory(last_detection, lang=lang)
    treat = adv["treatment"]

    if "dosage" in q or "how much" in q or "खुराक" in q or "அளவு" in q:
        return f"⚖️ Recommended Dosage for {adv['display_name']}:\n{treat['dosage']}\n\nChemical: {treat['chemical']}"
    elif "organic" in q or "natural" in q or "जैविक" in q or "இயற்கை" in q:
        return f"🌱 Organic Treatment for {adv['display_name']}:\n{treat['organic']}\n\nPreventive Practice: {treat['preventive']}"
    elif "chemical" in q or "pesticide" in q or "रासायनिक" in q or "மருந்து" in q:
        return f"🧪 Chemical Treatment for {adv['display_name']}:\n{treat['chemical']}\n\nDosage: {treat['dosage']}"
    elif "prevent" in q or "stop" in q or "रोकथाम" in q or "தடுக்க" in q:
        return f"🛡️ Preventive Measures for {adv['display_name']}:\n{treat['preventive']}"
    else:
        return (
            f"🤖 *AgriBot Assistant* for *{adv['display_name']}*:\n"
            f"• Symptoms: {adv['symptoms']}\n"
            f"• Organic Solution: {treat['organic']}\n"
            f"• Chemical Solution: {treat['chemical']}\n"
            f"• Dosage: {treat['dosage']}\n\n"
            f"You can ask me: 'What is the chemical dosage?', 'Give organic remedy', or 'How to prevent this?'"
        )


def main():
    parser = argparse.ArgumentParser(description="Test Farmer Advisory & SMS/WhatsApp System.")
    parser.add_argument("--test", action="store_true", help="Run self-test on all classes and translations")
    parser.add_argument("--class-name", default="rice_pest_yellow_stem_borer", help="Class to query")
    parser.add_argument("--lang", default="en", help="Language code (en, hi, ta, sw, es)")
    args = parser.parse_args()

    if args.test:
        print("=" * 60)
        print("  FARMER ADVISORY SYSTEM TEST")
        print("=" * 60)
        for cls in AGRONOMIC_KNOWLEDGE_BASE.keys():
            adv = get_treatment_advisory(cls, lang="en")
            print(f"✅ Class: {cls:<35} | Display: {adv['display_name']}")
        
        sample_dets = [{"class": "rice_pest_yellow_stem_borer", "confidence": 0.94}]
        print("\n--- Sample SMS Alert (English) ---")
        print(generate_sms_alert(sample_dets, farmer_name="Ramesh", lang="en"))
        print("\n--- Sample SMS Alert (Hindi) ---")
        print(generate_sms_alert(sample_dets, farmer_name="रमेश", lang="hi"))
        print("\n--- Sample WhatsApp Payload ---")
        print(json.dumps(generate_whatsapp_payload(sample_dets, lang="en"), indent=2))
    else:
        adv = get_treatment_advisory(args.class_name, lang=args.lang)
        print(json.dumps(adv, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

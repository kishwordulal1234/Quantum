from flask import Flask, render_template_string, request, jsonify
import google.generativeai as genai
import json
import time
import random
import string
import requests
from geopy.geocoders import Nominatim 

app = Flask(__name__)
app.secret_key = '7894'

GEMINI_API_KEY = "AIzaSyCvBWwt3MzxKYBFo761T93qsG0-0knnnhA"
genai.configure(api_key=GEMINI_API_KEY)

try:
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    print(f"Error initializing Gemini model: {e}")
    model = None

# Google Maps API configuration
GOOGLE_MAPS_API_KEY = "AIzaSyWbajdhrdz7VVOESVuo8nQBGUmlERWDf_v"

# Update the API configuration
GOMAPS_API_KEY = "your_gomaps_api_key"  
def get_nearby_hospitals(severity, lat, lng):

    try:
   
        base_url = "https://addressvalidation.gomaps.pro/v1"
        
        headers = {
            'Content-Type': 'application/json'
        }
        
  
        search_data = {
            "location": {
                "latitude": lat,
                "longitude": lng
            },
            "radius": 5000 if severity == "CRITICAL" else 10000,  # 5km for critical, 10km for moderate
            "type": "hospital",
            "limit": 5
        }
        
        response = requests.post(
            f"{base_url}/search?key={GOMAPS_API_KEY}",
            headers=headers,
            json=search_data
        )
        
        if response.status_code == 200:
            results = response.json().get("results", [])
            hospitals = []
            
            for place in results:
                # Get additional details for each hospital
                details_data = {
                    "placeId": place["place_id"],
                    "fields": ["formatted_address", "formatted_phone_number", "geometry"]
                }
                
                details_response = requests.post(
                    f"{base_url}/details?key={GOMAPS_API_KEY}",
                    headers=headers,
                    json=details_data
                )
                
                if details_response.status_code == 200:
                    details = details_response.json()
                    
                    hospitals.append({
                        "name": place.get("name", "Unknown Hospital"),
                        "vicinity": details.get("formatted_address", "Address not available"),
                        "phone": details.get("formatted_phone_number", "N/A"),
                        "geometry": details.get("geometry", {}),
                        "place_id": place["place_id"],
                        "distance": calculate_distance(lat, lng, 
                                                    details["geometry"]["location"]["lat"],
                                                    details["geometry"]["location"]["lng"]),
                        "maps_url": f"https://www.gomaps.pro/place/{place['place_id']}"
                    })
            
            return hospitals
            
        return []
    except Exception as e:
        print(f"Error fetching hospitals: {str(e)}")
        return []

def calculate_distance(lat1, lon1, lat2, lon2):
    
    from math import sin, cos, sqrt, atan2, radians
    
    R = 6371  
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return round(distance, 1)


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>quantum bio-link</title>
    <title>Advanced Medical Symptom Analyzer</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        :root {
            --primary-bg: #ffffff;
            --secondary-bg: #f3f4f6;
            --primary-text: #1f2937;
            --secondary-text: #4b5563;
            --accent-color: #3b82f6;
            --border-color: #e5e7eb;
            --card-bg: #ffffff;
            --input-bg: #ffffff;
            --input-text: #1f2937;
            --input-border: #e5e7eb;
            --input-placeholder: #9ca3af;
            --input-focus-border: #3b82f6;
            --input-focus-ring: rgba(59, 130, 246, 0.1);
            --warning-bg: #fef3c7;
            --warning-text: #92400e;
            --warning-border: #f59e0b;
            --symptom-tag-bg: #dbeafe;
            --symptom-tag-text: #1e40af;
            --loader-bg: #f3f4f6;
        }

        [data-theme="dark"] {
            --primary-bg: #111827;
            --secondary-bg: #1f2937;
            --primary-text: #f9fafb;
            --secondary-text: #d1d5db;
            --accent-color: #60a5fa;
            --border-color: #374151;
            --card-bg: #1f2937;
            --input-bg: #374151;
            --input-text: #f9fafb;
            --input-border: #4b5563;
            --input-placeholder: #9ca3af;
            --input-focus-border: #60a5fa;
            --input-focus-ring: rgba(96, 165, 250, 0.1);
            --warning-bg: #422006;
            --warning-text: #fef3c7;
            --warning-border: #d97706;
            --symptom-tag-bg: #1e3a8a;
            --symptom-tag-text: #bfdbfe;
            --loader-bg: #374151;
        }

        body {
            background-color: var(--primary-bg);
            color: var(--primary-text);
            transition: all 0.3s ease;
        }

        .theme-card {
            background-color: var(--card-bg);
            border-color: var(--border-color);
        }

        .theme-text {
            color: var(--primary-text);
        }

        .theme-text-secondary {
            color: var(--secondary-text);
        }

        .theme-border {
            border-color: var(--border-color);
        }

        .loader {
            border: 5px solid var(--loader-bg);
            border-top: 5px solid var(--accent-color);
        }

        .overlay {
            background-color: rgba(0, 0, 0, 0.5);
        }

        .warning-box {
            background-color: var(--warning-bg);
            border-color: var(--warning-border);
            color: var(--warning-text);
        }

        .symptom-tag {
            background-color: var(--symptom-tag-bg);
            color: var(--symptom-tag-text);
            transition: all 0.3s ease;
        }

        input, select, textarea {
            background-color: var(--input-bg);
            color: var(--input-text);
            border-color: var(--input-border);
        }

        input:focus, select:focus, textarea:focus {
            border-color: var(--input-focus-border);
            outline: none;
        }

        .radio-label {
            color: var(--primary-text);
        }

        .help-modal {
            background-color: var(--card-bg);
            color: var(--primary-text);
        }

        .theme-toggle {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .theme-toggle:hover {
            transform: scale(1.1);
            background-color: var(--secondary-bg);
        }

        .theme-toggle svg {
            fill: var(--primary-text);
        }

        /* Add smooth transitions for theme changes */
        * {
            transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
        }

        input[type="text"],
        input[type="number"],
        input[type="email"],
        textarea {
            background-color: var(--input-bg);
            color: var(--input-text);
            border: 1px solid var(--input-border);
            border-radius: 0.375rem;
            padding: 0.5rem 0.75rem;
            width: 100%;
            transition: all 0.3s ease;
        }

        input[type="text"]:focus,
        input[type="number"]:focus,
        input[type="email"]:focus,
        textarea:focus {
            outline: none;
            border-color: var(--input-focus-border);
            box-shadow: 0 0 0 3px var(--input-focus-ring);
        }

        input::placeholder {
            color: var(--input-placeholder);
        }

        /* Style for radio buttons and labels */
        .radio-group {
            display: flex;
            gap: 1rem;
        }

        .radio-label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--primary-text);
            cursor: pointer;
        }

        input[type="radio"] {
            accent-color: var(--accent-color);
        }

        /* Update the patient information section */
        .input-label {
            color: var(--secondary-text);
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }

        .loader-ring {
            width: 50px;
            height: 50px;
            border: 3px solid var(--border-color);
            border-radius: 50%;
            border-top-color: var(--accent-color);
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }

        .medical-icon {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 1.5rem;
        }

        @keyframes spin {
            to {transform: rotate(360deg);}
        }

        .loading-progress-transition {
            transition: width 300ms ease-out;
        }
    </style>
</head>
<body class="min-h-screen" data-theme="light">
    <!-- Progress Bar -->
    <div class="fixed top-0 left-0 right-0 theme-card shadow-md z-40">
        <div class="container mx-auto px-4 py-3">
            <div class="flex justify-between items-center">
                <div id="progressSteps" class="flex space-x-4">
                    <div class="progress-step flex items-center">
                        <div class="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center">1</div>
                        <span class="ml-2 text-sm theme-text">Patient Info</span>
                    </div>
                    <div class="progress-step flex items-center opacity-50">
                        <div class="w-8 h-8 rounded-full bg-gray-300 text-white flex items-center justify-center">2</div>
                        <span class="ml-2 text-sm theme-text">Symptoms</span>
                    </div>
                    <div class="progress-step flex items-center opacity-50">
                        <div class="w-8 h-8 rounded-full bg-gray-300 text-white flex items-center justify-center">3</div>
                        <span class="ml-2 text-sm theme-text">Analysis</span>
                    </div>
                </div>
                <div class="flex items-center space-x-4">
                    <button id="helpBtn" class="text-blue-500 hover:text-blue-700">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </button>
                    <button id="themeToggle" class="theme-toggle p-2 rounded-full">
                        <svg id="sunIcon" class="w-6 h-6 hidden" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                            <path fill-rule="evenodd" d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.166a.75.75 0 00-1.06-1.06l-1.591 1.59a.75.75 0 101.06 1.061l1.591-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.834 18.894a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 10-1.061 1.06l1.59 1.591zM12 18a.75.75 0 01.75.75V21a.75.75 0 01-1.5 0v-2.25A.75.75 0 0112 18zM7.758 17.303a.75.75 0 00-1.061-1.06l-1.591 1.59a.75.75 0 001.06 1.061l1.591-1.59zM6 12a.75.75 0 01-.75.75H3a.75.75 0 010-1.5h2.25A.75.75 0 016 12zM6.697 7.757a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 00-1.061 1.06l1.59 1.591z" />
                        </svg>
                        <svg id="moonIcon" class="w-6 h-6" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                            <path fill-rule="evenodd" d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69.75.75 0 01.981.98 10.503 10.503 0 01-9.694 6.46c-5.799 0-10.5-4.701-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 01.818.162z" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Loading Overlay -->
    <div id="loadingOverlay" class="hidden fixed inset-0 loading-overlay flex items-center justify-center z-50">
        <div class="theme-card p-8 rounded-lg shadow-lg max-w-md w-full mx-4">
            <div class="text-center">
                <div class="relative mb-6">
                    <div class="loader-ring"></div>
                    <div class="medical-icon">🏥</div>
                </div>
                <h3 class="text-xl font-bold mb-4">Analyzing Symptoms</h3>
                <div id="loadingProgress" class="space-y-4">
                    <div class="text-sm text-center mb-2" id="loadingStepText">Processing your description...</div>
                    <div class="h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div id="loadingProgressBar" 
                             class="h-full bg-blue-500 rounded-full transition-all duration-300 ease-out"
                             style="width: 0%">
                        </div>
                    </div>
                    <div class="text-sm text-right" id="loadingPercentage">0%</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Help Modal -->
    <div id="helpModal" class="hidden fixed inset-0 overlay flex items-center justify-center z-50">
        <div class="help-modal p-8 rounded-lg shadow-lg max-w-md animate__animated animate__fadeInDown">
            <h3 class="text-xl font-bold mb-4 theme-text">How to Use the Analyzer</h3>
            <ol class="list-decimal pl-5 space-y-2 mb-4 theme-text-secondary">
                <li>Enter your basic information</li>
                <li>Add your symptoms one by one</li>
                <li>Use suggested symptoms or type your own</li>
                <li>Review the analysis results</li>
                <li>Save or print your report if needed</li>
            </ol>
            <button id="closeHelp" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 w-full">Got it!</button>
        </div>
    </div>

    <div class="container mx-auto px-4 py-20 max-w-2xl">
        <h1 class="text-4xl font-bold text-center mb-8 text-blue-600 animate__animated animate__fadeIn">
                quantum bio-link
            🏥 Advanced Medical Symptom Analyzer
        </h1>
        
        <!-- Disclaimer -->
        <div class="warning-box border-l-4 p-4 mb-8 animate__animated animate__fadeIn">
            <p class="text-yellow-700">
                ⚠️ <strong>DISCLAIMER:</strong> This is a prototype medical analysis tool. 
                The results should not be considered as professional medical advice. 
                Always consult with a qualified healthcare provider for proper diagnosis and treatment.
            </p>
        </div>

        <!-- Patient Information Section -->
        <div id="nameSection" class="theme-card shadow-lg rounded-lg px-8 pt-6 pb-8 mb-4 animate__animated animate__fadeIn">
            <h2 class="text-2xl font-semibold mb-6 theme-text">Patient Information</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="mb-4">
                    <label class="input-label" for="patientName">
                        Full Name:
                    </label>
                    <input class="theme-input"
                           id="patientName" 
                           type="text" 
                           placeholder="Your name">
                </div>
                <div class="mb-4">
                    <label class="input-label" for="patientAge">
                        Age:
                    </label>
                    <input class="theme-input"
                           id="patientAge" 
                           type="number" 
                           min="0" 
                           max="120" 
                           placeholder="Your age">
                </div>
            </div>
            <div class="mb-4">
                <label class="input-label">Gender:</label>
                <div class="radio-group">
                    <label class="radio-label">
                        <input type="radio" name="gender" value="male">
                        <span>Male</span>
                    </label>
                    <label class="radio-label">
                        <input type="radio" name="gender" value="female">
                        <span>Female</span>
                    </label>
                    <label class="radio-label">
                        <input type="radio" name="gender" value="other">
                        <span>Other</span>
                    </label>
                </div>
            </div>
            <button id="submitName" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-full focus:outline-none focus:shadow-outline transform transition hover:scale-105">
                Continue
            </button>
        </div>

        <!-- Symptoms Section -->
        <div id="symptomsSection" class="hidden theme-card rounded-lg p-6 mb-6">
            <h2 class="text-2xl font-bold mb-4">Enter Your Symptoms</h2>
            
            <!-- Regular Symptoms Input -->
            <div id="regularSymptoms">
                <div class="mb-4">
                    <label class="block text-sm font-medium mb-2">Common Symptoms:</label>
                    <div class="flex flex-wrap gap-2" id="commonSymptoms">
                        <button class="symptom-tag px-3 py-1 rounded-full">Headache</button>
                        <button class="symptom-tag px-3 py-1 rounded-full">Fever</button>
                        <button class="symptom-tag px-3 py-1 rounded-full">Cough</button>
                        <button class="symptom-tag px-3 py-1 rounded-full">Fatigue</button>
                        <button class="symptom-tag px-3 py-1 rounded-full">Nausea</button>
                    </div>
                </div>
                
                <div class="mb-4">
                    <p class="text-gray-400 mb-2">Symptom <span id="symptomCounter">1</span> of 7:</p>
                    <div class="flex gap-2">
                        <input type="text" id="symptomInput" class="flex-1 rounded-md p-2" 
                               placeholder="Type or select a symptom">
                        <button id="addSymptom" class="bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600">
                            Add
                        </button>
                    </div>
                </div>

                <div id="symptomsList" class="mt-4 space-y-2"></div>
                
                <div class="mt-6 flex justify-between items-center">
                    <button id="analyzeSymptoms" class="hidden bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600">
                        Analyze Symptoms
                    </button>
                    <p class="text-sm text-gray-400">* Add at least one symptom to continue</p>
                </div>

                <!-- Mode Switch Button -->
                <div class="mt-4 pt-4 border-t border-gray-700">
                    <button id="switchMode" class="text-blue-400 hover:text-blue-500 text-sm">
                        Switch to Paragraph Mode
                    </button>
                </div>
            </div>

            <!-- Paragraph Mode -->
            <div id="paragraphMode" class="hidden">
                <div class="mb-4">
                    <label class="block text-sm font-medium mb-2">
                        Describe your symptoms and concerns in detail:
                    </label>
                    <div class="relative">
                        <textarea 
                            id="symptomParagraph" 
                            class="w-full h-32 rounded-md p-2 bg-gray-800 text-gray-100 border border-gray-700"
                            placeholder="Example: For the past few days, I've been experiencing a persistent headache along with fever. The pain is concentrated..."
                        ></textarea>
                        <button id="micButton" class="absolute bottom-2 right-2 p-2 bg-blue-500 hover:bg-blue-600 rounded-full transition-colors">
                            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                      d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                            </svg>
                        </button>
                    </div>
                    <div id="recordingStatus" class="hidden mt-2 text-sm text-green-400">
                        Recording... Click microphone again to stop
                    </div>
                </div>
                
                <div class="flex justify-between items-center">
                    <button id="analyzeParagraph" class="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600">
                        Analyze Description
                    </button>
                    <button id="backToSymptoms" class="text-blue-400 hover:text-blue-500 text-sm">
                        Back to Symptom Mode
                    </button>
                </div>
            </div>
        </div>

        <!-- Analysis Results -->
        <div id="analysisResult" class="hidden animate__animated animate__fadeIn">
            <div class="theme-card rounded-lg shadow-lg p-8 mb-8">
                <div class="flex justify-between items-center mb-6">
                    <h1 class="text-3xl font-bold text-blue-600">🏥 Medical Analysis Report</h1>
                    <div class="theme-text-secondary text-sm" id="analysisDate"></div>
                </div>
                
                <div class="bg-orange-50 dark:bg-orange-900 border-l-4 border-orange-500 text-orange-700 dark:text-orange-200 p-4 mb-6 rounded-r">
                    <p class="font-bold">⚠️ DISCLAIMER:</p>
                    <p class="text-sm">This is a prototype medical analysis tool. The results should not be considered as professional medical advice. Always consult with a qualified healthcare provider for proper diagnosis and treatment.</p>
                </div>

                <div class="grid md:grid-cols-2 gap-6 mb-8">
                    <div class="theme-card-secondary p-4 rounded-lg">
                        <h2 class="text-xl font-semibold mb-3 theme-text">Patient Information</h2>
                        <div class="space-y-2">
                            <p><span class="font-medium">Name:</span> <span id="resultName" class="theme-text-secondary"></span></p>
                            <p><span class="font-medium">Age:</span> <span id="resultAge" class="theme-text-secondary"></span></p>
                            <p><span class="font-medium">Gender:</span> <span id="resultGender" class="theme-text-secondary"></span></p>
                        </div>
                    </div>
                    <div class="theme-card-secondary p-4 rounded-lg">
                        <h2 class="text-xl font-semibold mb-3 theme-text">Reported Symptoms</h2>
                        <div id="resultSymptoms" class="flex flex-wrap gap-2"></div>
                    </div>
                </div>

                <div class="mb-8">
                    <h2 class="text-2xl font-semibold mb-4 theme-text">Potential Conditions</h2>
                    <div id="conditions" class="space-y-4"></div>
                </div>

                <div class="theme-card-secondary p-6 rounded-lg">
                    <h2 class="text-xl font-semibold mb-3 theme-text">Recommended Actions</h2>
                    <ul id="recommendations" class="list-disc list-inside space-y-2 theme-text-secondary"></ul>
                </div>

                <!-- Treatment Options -->
                <div class="grid md:grid-cols-2 gap-6 mb-6">
                    <!-- Herbal Remedies -->
                    <div class="bg-gray-800 p-4 rounded-lg">
                        <h2 class="text-xl font-semibold mb-3 text-green-400">Natural & Herbal Remedies</h2>
                        <div class="space-y-4">
                            ${(result.herbal_remedies || []).map(remedy => `
                                <div class="border border-gray-700 rounded p-3">
                                    <h3 class="font-medium text-green-300 mb-2">${remedy.name}</h3>
                                    <div class="space-y-2 text-sm">
                                        <p><span class="font-medium">Ingredients:</span> ${remedy.ingredients.join(', ')}</p>
                                        <p><span class="font-medium">Preparation:</span> ${remedy.preparation}</p>
                                        <p><span class="font-medium">Usage:</span> ${remedy.usage}</p>
                                        <p><span class="font-medium">Benefits:</span> ${remedy.benefits}</p>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <!-- Allopathic Medicines -->
                    <div class="bg-gray-800 p-4 rounded-lg">
                        <h2 class="text-xl font-semibold mb-3 text-yellow-400">Allopathic Medicines</h2>
                        <div class="bg-red-900/50 border-l-4 border-red-500 p-3 mb-4 rounded-r">
                            <p class="text-sm text-red-200">
                                ⚠️ <strong>IMPORTANT WARNING:</strong> These medicine suggestions are for reference only. 
                                Never take any medication without proper consultation with a qualified healthcare provider.
                            </p>
                        </div>
                        <div class="space-y-4">
                            ${(result.allopathic_medicines || []).map(medicine => `
                                <div class="border border-gray-700 rounded p-3">
                                    <h3 class="font-medium text-yellow-300 mb-2">${medicine.name}</h3>
                                    <div class="space-y-2 text-sm">
                                        <p><span class="font-medium">Type:</span> ${medicine.type}</p>
                                        <p><span class="font-medium">Typical Dosage:</span> ${medicine.typical_dosage}</p>
                                        <div class="mt-2">
                                            <p class="font-medium text-red-400">Warnings & Side Effects:</p>
                                            <ul class="list-disc list-inside text-red-300">
                                                ${medicine.warnings.map(warning => `
                                                    <li>${warning}</li>
                                                `).join('')}
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>

                <!-- Additional Disclaimer -->
                <div class="bg-orange-900/50 border-l-4 border-orange-500 p-4 mb-6 rounded-r">
                    <p class="text-sm text-orange-200">
                        <strong>📢 MEDICATION DISCLAIMER:</strong> The medicine suggestions provided here, both herbal and allopathic, 
                        are based on common treatments for the identified symptoms. Individual responses to medications can vary significantly. 
                        Always consult with a qualified healthcare provider before starting any medication or treatment plan. They can provide 
                        proper diagnosis and consider your specific medical history, current medications, and potential contraindications.
                    </p>
                </div>

                <div class="mt-8 text-center">
                    <button onclick="resetAnalysis()" class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition-colors">
                        Start New Analysis
                    </button>
                </div>
            </div>
        </div>

        <script>
            // Theme handling
            const themeToggle = document.getElementById('themeToggle');
            const sunIcon = document.getElementById('sunIcon');
            const moonIcon = document.getElementById('moonIcon');

            // Check for saved theme preference or system preference
            const savedTheme = localStorage.getItem('theme') || 
                (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
            document.body.setAttribute('data-theme', savedTheme);
            updateThemeIcons(savedTheme);

            themeToggle.addEventListener('click', () => {
                const currentTheme = document.body.getAttribute('data-theme');
                const newTheme = currentTheme === 'light' ? 'dark' : 'light';
                
                document.body.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);
                updateThemeIcons(newTheme);
            });

            function updateThemeIcons(theme) {
                if (theme === 'dark') {
                    moonIcon.classList.add('hidden');
                    sunIcon.classList.remove('hidden');
                } else {
                    sunIcon.classList.add('hidden');
                    moonIcon.classList.remove('hidden');
                }
            }

            // Listen for system theme changes
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
                const newTheme = e.matches ? 'dark' : 'light';
                if (!localStorage.getItem('theme')) {  // Only if user hasn't set a preference
                    document.body.setAttribute('data-theme', newTheme);
                    updateThemeIcons(newTheme);
                }
            });

            let patientName = '';
            let patientAge = '';
            let patientGender = '';
            let symptoms = [];
            const MAX_SYMPTOMS = 7;

            // Help Modal
            document.getElementById('helpBtn').addEventListener('click', () => {
                document.getElementById('helpModal').classList.remove('hidden');
            });

            document.getElementById('closeHelp').addEventListener('click', () => {
                document.getElementById('helpModal').classList.add('hidden');
            });

            // Progress Steps
            function updateProgress(step) {
                const steps = document.querySelectorAll('.progress-step');
                steps.forEach((s, index) => {
                    if (index < step) {
                        s.classList.remove('opacity-50');
                        s.querySelector('div').classList.add('bg-blue-500');
                        s.querySelector('div').classList.remove('bg-gray-300');
                    } else if (index === step) {
                        s.classList.remove('opacity-50');
                        s.classList.add('active');
                    } else {
                        s.classList.add('opacity-50');
                        s.querySelector('div').classList.add('bg-gray-300');
                        s.querySelector('div').classList.remove('bg-blue-500');
                    }
                });
            }

            // Common Symptoms
            document.getElementById('commonSymptoms').addEventListener('click', (e) => {
                if (e.target.classList.contains('symptom-tag')) {
                    document.getElementById('symptomInput').value = e.target.textContent;
                }
            });

            // Name Section Handling
            document.getElementById('submitName').addEventListener('click', () => {
                patientName = document.getElementById('patientName').value.trim();
                patientAge = document.getElementById('patientAge').value.trim();
                patientGender = document.querySelector('input[name="gender"]:checked')?.value;

                if (patientName && patientAge && patientGender) {
                    document.getElementById('nameSection').classList.add('hidden');
                    document.getElementById('symptomsSection').classList.remove('hidden');
                    updateProgress(1);
                } else {
                    alert('Please fill in all required information');
                }
            });

            // Symptoms Handling
            document.getElementById('addSymptom').addEventListener('click', () => {
                const symptomInput = document.getElementById('symptomInput');
                const symptom = symptomInput.value.trim();
                
                if (symptom && !symptoms.includes(symptom)) {
                    if (symptoms.length >= MAX_SYMPTOMS) {
                        alert('Maximum number of symptoms reached');
                        return;
                    }
                    
                    symptoms.push(symptom);
                    updateSymptomsList();
                    symptomInput.value = '';
                    
                    // Show analyze button after first symptom
                    document.getElementById('analyzeSymptoms').classList.remove('hidden');
                    
                    // Update symptom counter
                    document.getElementById('symptomCounter').textContent = symptoms.length + 1;
                }
            });

            function updateSymptomsList() {
                const list = document.getElementById('symptomsList');
                list.innerHTML = symptoms.map((symptom, index) => `
                    <div class="flex justify-between items-center theme-card p-2 rounded">
                        <span class="theme-text">${symptom}</span>
                        <button onclick="removeSymptom(${index})" class="text-red-500 hover:text-red-700">×</button>
                    </div>
                `).join('');
            }

            function removeSymptom(index) {
                symptoms.splice(index, 1);
                updateSymptomsList();
                document.getElementById('symptomCounter').textContent = symptoms.length + 1;
                if (symptoms.length === 0) {
                    document.getElementById('analyzeSymptoms').classList.add('hidden');
                }
            }

            // Analysis
            document.getElementById('analyzeSymptoms').addEventListener('click', async () => {
                if (symptoms.length === 0) {
                    alert('Please add at least one symptom');
                    return;
                }

                document.getElementById('loadingOverlay').classList.remove('hidden');
                updateLoadingProgress();

                try {
                    const response = await fetch('/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            name: patientName,
                            age: patientAge,
                            gender: patientGender,
                            symptoms: symptoms
                        })
                    });

                    const result = await response.json();
                    if (result.error) {
                        throw new Error(result.error);
                    }

                    displayAnalysisResult(result);
                } catch (error) {
                    alert('Analysis failed: ' + error.message);
                } finally {
                    document.getElementById('loadingOverlay').classList.add('hidden');
                }
            });

            async function displayAnalysisResult(result) {
                const analysisResult = document.getElementById('analysisResult');
                document.getElementById('symptomsSection').classList.add('hidden');
                analysisResult.classList.remove('hidden');

                // Check for critical/moderate conditions
                const isCriticalOrModerate = result.conditions.some(c => 
                    ["CRITICAL", "MODERATE"].includes(c.severity?.toUpperCase())
                );

                analysisResult.innerHTML = `
                    <div class="theme-card rounded-lg p-6">
                        <!-- Medical Analysis Report Header -->
                        <div class="flex justify-between items-center mb-6">
                            <div class="flex items-center gap-2">
                                <span class="text-2xl">👨‍⚕️</span>
                                <h1 class="text-2xl font-bold">Medical Analysis Report</h1>
                            </div>
                            <div class="text-sm text-gray-400">${new Date().toLocaleString()}</div>
                        </div>

                        <!-- Disclaimer -->
                        <div class="bg-orange-900/30 border-l-4 border-orange-500 p-4 mb-6 rounded-r">
                            <p class="text-sm text-orange-200">
                                ⚠️ <strong>DISCLAIMER:</strong> This is an AI-generated analysis and should not be considered as professional medical advice. Please consult with a qualified healthcare provider for proper diagnosis and treatment.
                            </p>
                        </div>

                        <!-- Patient Information -->
                        <div class="grid md:grid-cols-2 gap-6 mb-6">
                            <div>
                                <h2 class="text-xl font-semibold mb-3">Patient Information</h2>
                                <div class="space-y-2">
                                    <p><span class="font-medium">Name:</span> ${result.name}</p>
                                    <p><span class="font-medium">Age:</span> ${result.age}</p>
                                    <p><span class="font-medium">Gender:</span> ${result.gender}</p>
                                </div>
                            </div>
                            <div>
                                <h2 class="text-xl font-semibold mb-3">Identified Symptoms</h2>
                                <div class="flex flex-wrap gap-2">
                                    ${result.extracted_symptoms.map(symptom => 
                                        `<span class="bg-blue-500 text-white px-3 py-1 rounded-full text-sm">${symptom}</span>`
                                    ).join('')}
                                </div>
                            </div>
                        </div>

                        <!-- Conditions Section -->
                        <div class="mb-6">
                            <h2 class="text-xl font-semibold mb-3">Potential Conditions</h2>
                            ${result.conditions.map(condition => `
                                <div class="bg-gray-800 rounded-lg p-4 mb-4">
                                    <div class="flex items-center justify-between mb-2">
                                        <h3 class="text-lg font-medium">${condition.name}</h3>
                                        <span class="bg-blue-500 text-white text-sm px-2 py-1 rounded-full">
                                            Confidence: ${condition.confidence}%
                                        </span>
                                    </div>
                                    <p class="text-gray-300 mb-3">${condition.description}</p>
                                    <div class="bg-${condition.severity.toLowerCase() === 'critical' ? 'red' : condition.severity.toLowerCase() === 'moderate' ? 'yellow' : 'green'}-900/30 p-3 rounded-lg">
                                        <p class="font-medium text-${condition.severity.toLowerCase() === 'critical' ? 'red' : condition.severity.toLowerCase() === 'moderate' ? 'yellow' : 'green'}-400">
                                            Severity: ${condition.severity}
                                        </p>
                                        <p class="text-sm mt-1">${condition.severity_explanation}</p>
                                    </div>
                                </div>
                            `).join('')}
                        </div>

                        ${isCriticalOrModerate ? `
                            <!-- Emergency Section -->
                            <div class="bg-gray-800 p-4 rounded-lg mb-6">
                                <div class="flex items-center justify-between mb-4">
                                    <h2 class="text-xl font-semibold flex items-center gap-2">
                                        🚨 Emergency Services
                                        ${result.conditions.some(c => c.severity?.toUpperCase() === "CRITICAL") ? 
                                            '<span class="bg-red-500 text-white text-xs px-2 py-1 rounded-full">URGENT CARE NEEDED</span>' : 
                                            '<span class="bg-yellow-500 text-white text-xs px-2 py-1 rounded-full">Medical Attention Recommended</span>'
                                        }
                                    </h2>
                                </div>

                                <!-- Hospital Search -->
                                <div class="grid grid-cols-2 gap-4 mb-4">
                                    <a href="https://www.google.com/maps/search/hospitals+near+me" 
                                       target="_blank"
                                       class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-3 rounded-lg text-center flex items-center justify-center gap-2 transition-colors">
                                        <span>🔍</span> Find Nearby Hospitals
                                    </a>
                                    <a href="https://www.practo.com/hospitals" 
                                       target="_blank"
                                       class="bg-green-500 hover:bg-green-600 text-white px-4 py-3 rounded-lg text-center flex items-center justify-center gap-2 transition-colors">
                                        <span>🏥</span> Search on Practo
                                    </a>
                                </div>

                                <!-- Emergency Numbers -->
                                <div class="bg-red-900/30 border border-red-500 rounded-lg p-4">
                                    <h3 class="text-lg font-semibold mb-3 text-red-400">Emergency Contacts</h3>
                                    <div class="grid grid-cols-2 gap-4">
                                        <a href="tel:102" class="bg-red-500 hover:bg-red-600 text-white p-4 rounded-lg flex items-center gap-3 transition-colors">
                                            <span class="text-2xl">🚑</span>
                                            <div>
                                                <div class="font-bold">Ambulance</div>
                                                <div class="text-sm opacity-90">102</div>
                                            </div>
                                        </a>
                                        <a href="tel:108" class="bg-red-500 hover:bg-red-600 text-white p-4 rounded-lg flex items-center gap-3 transition-colors">
                                            <span class="text-2xl">🆘</span>
                                            <div>
                                                <div class="font-bold">Emergency</div>
                                                <div class="text-sm opacity-90">108</div>
                                            </div>
                                        </a>
                                    </div>
                                </div>
                            </div>
                        ` : ''}

                        <!-- Recommendations -->
                        <div class="bg-gray-800 p-4 rounded-lg mb-6">
                            <h2 class="text-xl font-semibold mb-3">Recommended Actions</h2>
                            <ul class="list-disc list-inside space-y-2">
                                ${result.recommendations.map(rec => 
                                    `<li class="text-gray-300">${rec}</li>`
                                ).join('')}
                            </ul>
                        </div>

                        <!-- Treatment Options -->
                        <div class="grid md:grid-cols-2 gap-6 mb-6">
                            <!-- Herbal Remedies -->
                            <div class="bg-gray-800 p-4 rounded-lg">
                                <h2 class="text-xl font-semibold mb-3 text-green-400">Natural & Herbal Remedies</h2>
                                <div class="space-y-4">
                                    ${(result.herbal_remedies || []).map(remedy => `
                                        <div class="border border-gray-700 rounded p-3">
                                            <h3 class="font-medium text-green-300 mb-2">${remedy.name}</h3>
                                            <div class="space-y-2 text-sm">
                                                <p><span class="font-medium">Ingredients:</span> ${remedy.ingredients.join(', ')}</p>
                                                <p><span class="font-medium">Preparation:</span> ${remedy.preparation}</p>
                                                <p><span class="font-medium">Usage:</span> ${remedy.usage}</p>
                                                <p><span class="font-medium">Benefits:</span> ${remedy.benefits}</p>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>

                            <!-- Allopathic Medicines -->
                            <div class="bg-gray-800 p-4 rounded-lg">
                                <h2 class="text-xl font-semibold mb-3 text-yellow-400">Allopathic Medicines</h2>
                                <div class="bg-red-900/50 border-l-4 border-red-500 p-3 mb-4 rounded-r">
                                    <p class="text-sm text-red-200">
                                        ⚠️ <strong>IMPORTANT WARNING:</strong> These medicine suggestions are for reference only. 
                                        Never take any medication without proper consultation with a qualified healthcare provider.
                                    </p>
                                </div>
                                <div class="space-y-4">
                                    ${(result.allopathic_medicines || []).map(medicine => `
                                        <div class="border border-gray-700 rounded p-3">
                                            <h3 class="font-medium text-yellow-300 mb-2">${medicine.name}</h3>
                                            <div class="space-y-2 text-sm">
                                                <p><span class="font-medium">Type:</span> ${medicine.type}</p>
                                                <p><span class="font-medium">Typical Dosage:</span> ${medicine.typical_dosage}</p>
                                                <div class="mt-2">
                                                    <p class="font-medium text-red-400">Warnings & Side Effects:</p>
                                                    <ul class="list-disc list-inside text-red-300">
                                                        ${medicine.warnings.map(warning => `
                                                            <li>${warning}</li>
                                                        `).join('')}
                                                    </ul>
                                                </div>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        </div>

                        <!-- Report Footer -->
                        <div class="border-t border-gray-700 pt-4 mt-6">
                            <div class="flex justify-between items-center">
                                <div class="text-sm text-gray-400">
                                    Report ID: ${result.report_id || 'N/A'}
                                </div>
                                <div class="flex gap-4">
                                    <button onclick="location.reload()" 
                                            class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors">
                                        🔄 New Analysis
                                    </button>
                                    <button onclick="window.print()" 
                                            class="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors">
                                        🖨️ Print Report
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }

            function resetAnalysis() {
                patientName = '';
                patientAge = '';
                patientGender = '';
                symptoms = [];
                document.getElementById('analysisResult').classList.add('hidden');
                document.getElementById('nameSection').classList.remove('hidden');
                document.getElementById('symptomsSection').classList.add('hidden');
                document.getElementById('patientName').value = '';
                document.getElementById('patientAge').value = '';
                document.querySelectorAll('input[name="gender"]').forEach(radio => radio.checked = false);
                updateProgress(0);
            }

            // Mode switching
            document.getElementById('switchMode').addEventListener('click', () => {
                document.getElementById('regularSymptoms').classList.add('hidden');
                document.getElementById('paragraphMode').classList.remove('hidden');
            });

            document.getElementById('backToSymptoms').addEventListener('click', () => {
                document.getElementById('paragraphMode').classList.add('hidden');
                document.getElementById('regularSymptoms').classList.remove('hidden');
            });

            // Update the loading progress function
            function updateLoadingProgress() {
                const loadingStepText = document.getElementById('loadingStepText');
                const loadingProgressBar = document.getElementById('loadingProgressBar');
                const loadingPercentage = document.getElementById('loadingPercentage');
                
                if (!loadingStepText || !loadingProgressBar || !loadingPercentage) {
                    console.error('Loading elements not found');
                    return;
                }

                const steps = [
                    { text: 'Processing your description...', target: 33 },
                    { text: 'Analyzing symptoms...', target: 66 },
                    { text: 'Generating results...', target: 100 }
                ];

                let currentStep = 0;
                let currentProgress = 0;

                function animateProgress() {
                    if (currentStep >= steps.length) return;

                    const step = steps[currentStep];
                    const targetProgress = step.target;

                    const interval = setInterval(() => {
                        if (currentProgress >= targetProgress) {
                            clearInterval(interval);
                            currentStep++;
                            if (currentStep < steps.length) {
                                loadingStepText.textContent = steps[currentStep].text;
                                setTimeout(animateProgress, 200);
                            }
                        } else {
                            currentProgress++;
                            loadingProgressBar.style.width = `${currentProgress}%`;
                            loadingPercentage.textContent = `${currentProgress}%`;
                        }
                    }, 20);
                }

                // Start the animation
                animateProgress();
            }

            // Update the analyze paragraph function
            document.getElementById('analyzeParagraph').addEventListener('click', async () => {
                const text = document.getElementById('symptomParagraph').value.trim();
                if (!text) {
                    alert('Please describe your symptoms');
                    return;
                }

                const loadingOverlay = document.getElementById('loadingOverlay');
                if (loadingOverlay) {
                    loadingOverlay.classList.remove('hidden');
                    updateLoadingProgress();
                }

                try {
                    const response = await fetch('/analyze_paragraph', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            name: patientName,
                            age: patientAge,
                            gender: patientGender,
                            text: text
                        })
                    });

                    const result = await response.json();
                    if (result.error) {
                        throw new Error(result.error);
                    }

                    symptoms = result.extracted_symptoms || [];
                    displayAnalysisResult(result);
                } catch (error) {
                    alert('Analysis failed: ' + error.message);
                } finally {
                    if (loadingOverlay) {
                        loadingOverlay.classList.add('hidden');
                    }
                }
            });

            // Speech Recognition Setup
            let recognition = null;
            let isRecording = false;

            if ('webkitSpeechRecognition' in window) {
                recognition = new webkitSpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.lang = 'en-US';  // You can change this based on your needs

                recognition.onresult = (event) => {
                    const transcript = Array.from(event.results)
                        .map(result => result[0])
                        .map(result => result.transcript)
                        .join('');
                    
                    document.getElementById('symptomParagraph').value = transcript;
                };

                recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    stopRecording();
                };

                recognition.onend = () => {
                    stopRecording();
                };
            }

            document.getElementById('micButton').addEventListener('click', () => {
                if (!recognition) {
                    alert('Speech recognition is not supported in your browser. Please use Chrome or Edge.');
                    return;
                }

                if (!isRecording) {
                    // Start recording
                    recognition.start();
                    isRecording = true;
                    document.getElementById('recordingStatus').classList.remove('hidden');
                    document.getElementById('micButton').classList.add('bg-red-500');
                    document.getElementById('micButton').classList.remove('bg-blue-500');
                } else {
                    // Stop recording
                    recognition.stop();
                    stopRecording();
                }
            });

            function stopRecording() {
                isRecording = false;
                document.getElementById('recordingStatus').classList.add('hidden');
                document.getElementById('micButton').classList.remove('bg-red-500');
                document.getElementById('micButton').classList.add('bg-blue-500');
            }
        </script>
'''

def analyze_symptoms(name, symptoms):
    if not model:
        print("Model is not initialized.")
        return {"error": "Model not initialized"}

    unique_symptoms = list(set(symptoms))
    
    prompt = f"""Analyze these symptoms and provide a detailed medical analysis:
Patient: {name}
Symptoms: {', '.join(unique_symptoms)}

Provide a comprehensive analysis in this exact JSON format, ensuring all fields are properly filled:
{{
    "conditions": [
        {{
            "name": "Condition Name",
            "confidence": 85,
            "severity": "CRITICAL",  // Must be exactly one of: CRITICAL, MODERATE, or MILD
            "severity_explanation": "Detailed explanation of why this condition is considered critical/moderate/mild",
            "description": "Comprehensive explanation of the condition and how it relates to the symptoms",
            "urgency": "IMMEDIATE_ATTENTION"  // Must be exactly one of: IMMEDIATE_ATTENTION, SOON, or ROUTINE
        }}
    ],
    "recommendations": [
        "Specific action-oriented recommendation 1",
        "Specific action-oriented recommendation 2"
    ],
    "herbal_remedies": [
        {{
            "name": "Specific herbal remedy name",
            "ingredients": ["Detailed ingredient 1", "Detailed ingredient 2"],
            "preparation": "Step-by-step preparation instructions",
            "usage": "Specific usage instructions and frequency",
            "benefits": "Detailed benefits and expected outcomes",
            "precautions": "Important precautions and contraindications"
        }}
    ],
    "allopathic_medicines": [
        {{
            "name": "Specific medicine name",
            "type": "Specific medicine category",
            "typical_dosage": "Detailed dosage information",
            "warnings": [
                "Specific side effect or warning 1",
                "Specific side effect or warning 2",
                "Important contraindication"
            ],
            "usage_instructions": "Detailed instructions for use"
        }}
    ]
}}

For the given symptoms ({', '.join(unique_symptoms)}), provide:
1. Accurate severity levels (CRITICAL/MODERATE/MILD) based on medical severity
2. Clear urgency ratings (IMMEDIATE_ATTENTION/SOON/ROUTINE)
3. Detailed explanations for severity levels
4. Specific and relevant herbal remedies
5. Appropriate allopathic medicines with proper warnings
6. Comprehensive recommendations

Note: For potentially serious conditions like rabies, ensure proper severity and urgency levels are set."""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in response")
            
            json_str = response_text[start_idx:end_idx]
            result = json.loads(json_str)
            
            # Add report ID
            result['report_id'] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            # Add empty extracted_symptoms for consistency with paragraph mode
            if 'extracted_symptoms' not in result:
                result['extracted_symptoms'] = unique_symptoms
            
            return result

        except Exception as e:
            print(f"Error parsing response: {str(e)}")
            return {
                "report_id": "ERROR" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4)),
                "extracted_symptoms": unique_symptoms,
                "conditions": [
                    {
                        "name": "Analysis Error",
                        "confidence": 0,
                        "description": "Unable to process symptoms. Please try again."
                    }
                ],
                "recommendations": ["Please try again or contact support if the problem persists."],
                "herbal_remedies": [
                    {
                        "name": "Analysis Error",
                        "ingredients": [],
                        "preparation": "Unable to provide remedies at this time",
                        "usage": "Please try again",
                        "benefits": "N/A"
                    }
                ],
                "allopathic_medicines": [
                    {
                        "name": "Analysis Error",
                        "type": "N/A",
                        "typical_dosage": "N/A",
                        "warnings": ["Unable to provide medicine suggestions at this time"]
                    }
                ]
            }
            
    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        return {
            "report_id": "ERROR" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4)),
            "extracted_symptoms": unique_symptoms,
            "conditions": [
                {
                    "name": "System Error",
                    "confidence": 0,
                    "description": "An error occurred during analysis."
                }
            ],
            "recommendations": ["Please try again later."],
            "herbal_remedies": [
                {
                    "name": "System Error",
                    "ingredients": [],
                    "preparation": "Service temporarily unavailable",
                    "usage": "Please try again later",
                    "benefits": "N/A"
                }
            ],
            "allopathic_medicines": [
                {
                    "name": "System Error",
                    "type": "N/A",
                    "typical_dosage": "N/A",
                    "warnings": ["Service temporarily unavailable"]
                }
            ]
        }

def analyze_paragraph(text):
    if not model:
        print("Model is not initialized.")
        return {"error": "Model not initialized"}
    
    prompt = f"""As a medical analysis system, analyze this patient's description:

Patient's Description:
{text}

Extract key information and provide a comprehensive analysis in this exact JSON format:
{{
    "name": "",  // Leave empty if not provided in text
    "age": "",   // Leave empty if not provided in text
    "gender": "", // Leave empty if not provided in text
    "extracted_symptoms": [
        "symptom 1",
        "symptom 2"
    ],
    "conditions": [
        {{
            "name": "Condition Name",
            "confidence": 85,
            "severity": "CRITICAL",  // Must be exactly one of: CRITICAL, MODERATE, or MILD
            "severity_explanation": "Detailed explanation of why this condition is considered critical/moderate/mild",
            "description": "Comprehensive explanation of the condition and how it relates to the symptoms",
            "urgency": "IMMEDIATE_ATTENTION"  // Must be exactly one of: IMMEDIATE_ATTENTION, SOON, or ROUTINE
        }}
    ],
    "recommendations": [
        "Specific action-oriented recommendation 1",
        "Specific action-oriented recommendation 2"
    ],
    "herbal_remedies": [
        {{
            "name": "Specific herbal remedy name",
            "ingredients": ["Detailed ingredient 1", "Detailed ingredient 2"],
            "preparation": "Step-by-step preparation instructions",
            "usage": "Specific usage instructions and frequency",
            "benefits": "Detailed benefits and expected outcomes",
            "precautions": "Important precautions and contraindications"
        }}
    ],
    "allopathic_medicines": [
        {{
            "name": "Specific medicine name",
            "type": "Specific medicine category",
            "typical_dosage": "Detailed dosage information",
            "warnings": [
                "Specific side effect or warning 1",
                "Specific side effect or warning 2",
                "Important contraindication"
            ],
            "usage_instructions": "Detailed instructions for use"
        }}
    ]
}}

Ensure to:
1. Extract any patient information if present in the text
2. List all symptoms mentioned
3. Provide detailed condition analysis
4. Include severity and urgency levels
5. Give comprehensive recommendations
6. List both herbal and allopathic treatment options with proper warnings"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in response")
            
            json_str = response_text[start_idx:end_idx]
            result = json.loads(json_str)
            
            # Add report ID
            result['report_id'] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            return result

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            return {"error": "Invalid response format"}
            
    except Exception as e:
        print(f"Error in analyze_paragraph: {str(e)}")
        return {"error": "Analysis failed"}

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        name = data.get('name', '')
        age = data.get('age', '')
        gender = data.get('gender', '')
        symptoms = data.get('symptoms', [])
        
        if not symptoms:
            return jsonify({'error': 'No symptoms provided'}), 400
        
        if len(symptoms) > 7:
            return jsonify({'error': 'Maximum 7 symptoms allowed'}), 400
        
        analysis_result = analyze_symptoms(name, symptoms)
        if analysis_result.get('error'):
            return jsonify({'error': analysis_result['error']}), 500
            
        # Add patient info to the result
        analysis_result['name'] = name
        analysis_result['age'] = age
        analysis_result['gender'] = gender
            
        return jsonify(analysis_result)

    except Exception as e:
        print(f"Error in analyze route: {str(e)}")
        return jsonify({'error': 'Server error occurred'}), 500

@app.route('/analyze_paragraph', methods=['POST'])
def analyze_paragraph_route():
    try:
        data = request.json
        text = data.get('text', '')
        name = data.get('name', '')
        age = data.get('age', '')
        gender = data.get('gender', '')
        
        if not text:
            return jsonify({'error': 'No description provided'}), 400
        
        analysis_result = analyze_paragraph(text)
        if analysis_result.get('error'):
            return jsonify({'error': analysis_result['error']}), 500
        
        # Add patient info if provided
        analysis_result['name'] = name
        analysis_result['age'] = age
        analysis_result['gender'] = gender
            
        return jsonify(analysis_result)

    except Exception as e:
        print(f"Error in analyze_paragraph route: {str(e)}")
        return jsonify({'error': 'Server error occurred'}), 500

@app.route('/get_hospitals', methods=['POST'])
def get_hospitals():
    try:
        data = request.json
        hospitals = get_nearby_hospitals(
            data.get('severity'),
            data.get('lat'),
            data.get('lng')
        )
        return jsonify(hospitals)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
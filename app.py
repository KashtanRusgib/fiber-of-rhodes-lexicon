import streamlit as st
import os
import requests  # For Ideogram API
from openai import OpenAI
from google.cloud import aiplatform  # For Google Vertex AI (install via pip if needed: pip install google-cloud-aiplatform)
import gtts  # For TTS audio
from PIL import Image
import io
import arabic_reshaper
from bidi.algorithm import get_display  # For RTL text

# Initialize clients (add your keys in Streamlit secrets or env)
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
ideogram_api_key = os.environ.get('IDEOGRAM_API_KEY')  # Required for Ideogram
# For Google: Assume project setup; init aiplatform with your project ID
aiplatform.init(project=os.environ.get('GOOGLE_PROJECT_ID'), location='us-central1')  # Set your project/location

# Expanded term-root dict from your Gemini chat
TERM_ROOTS = {
    "Insertion Loss": {"root": "F-Q-D", "root_meaning": "To lose/miss", "arabic": "فقد الإدخال"},
    "Splicing": {"root": "L-H-M", "root_meaning": "Meat/Welding", "arabic": "لحام"},
    "Fiber Optics": {"root": "L-Y-F", "root_meaning": "Natural fiber/Loofah", "arabic": "الألياف البصرية"},
    "Attenuation": {"root": "T-W-H-N", "root_meaning": "To weaken", "arabic": "توهين"},
    "OTDR Device": {"root": "F-H-S", "root_meaning": "To examine", "arabic": "جهاز فحص الألياف"},
    "Trace (Graph)": {"root": "R-S-M", "root_meaning": "To draw", "arabic": "رسم بياني"},
    # Add more as needed from your list
}

def add_tashkeel(arabic_text):
    # Use OpenAI for better Tashkeel (vowel addition)
    prompt = f"Add accurate Tashkeel (diacritics) to this Arabic text for pronunciation: {arabic_text}"
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    voweled = response.choices[0].message.content
    reshaped = arabic_reshaper.reshape(voweled)
    return get_display(reshaped)

def generate_mnemonic(term, root, root_meaning):
    prompt = f"Create a humorous mnemonic story like 'Fun with Chinese Characters': Arabic root {root} means '{root_meaning}'. Link to fiber optic term '{term}' with a visual metaphor."
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def generate_image_dalle(story, root, term):
    image_prompt = f"Black-and-white cartoon in minimalist style: {story}. Label with Arabic root '{root}' in bold calligraphy and technical word below."
    response = openai_client.images.generate(
        model="dall-e-3",
        prompt=image_prompt,
        n=1,
        size="1024x1024"
    )
    return response.data[0].url

def generate_image_ideogram(story, root, term):
    payload = {
        "prompt": f"Black-and-white line drawing, humorous minimalist cartoon: {story}. Include bold Arabic calligraphy label for root '{root}' and term '{term}' below.",
        "model": "ideogram-3.0",  # Or your preferred model
        "style": "AUTO"  # Adjust for B&W cartoon
    }
    headers = {"Authorization": f"Bearer {ideogram_api_key}"}
    response = requests.post("https://api.ideogram.ai/generate", json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["data"][0]["url"]  # Assumes success; handle errors
    else:
        st.error("Ideogram API error")
        return None

def generate_image_google(story, root, term):
    # Using Vertex AI Imagen (example for Imagen 3)
    model = aiplatform.ImageGenerationModel.from_pretrained("imagen-3.0-fast-generate-preview-0514")
    response = model.generate_images(
        prompt=f"Black-and-white minimalist cartoon: {story}. Label with Arabic root '{root}' in calligraphy and '{term}' below.",
        number_of_images=1,
        aspect_ratio="1:1"
    )
    # Save and return URL (or base64); for simplicity, assume you save to temp file and host
    img_data = response.images[0]._as_base64_string()
    return f"data:image/png;base64,{img_data}"  # Inline base64 for Streamlit

# Streamlit UI
st.title("Colossus Lexicon: Arabic Fiber Tech Mnemonics")

api_choice = st.selectbox("Select Image Generation API:", ["DALL-E (OpenAI)", "Ideogram", "Google Vertex AI"])

term = st.selectbox("Select or enter a fiber optic term:", list(TERM_ROOTS.keys()) + ["Custom..."])
if term == "Custom...":
    term = st.text_input("Enter custom term:")
    root = st.text_input("Enter root (e.g., F-Q-D):")
    root_meaning = st.text_input("Enter root meaning:")
    arabic = st.text_input("Enter Arabic script:")
else:
    data = TERM_ROOTS.get(term, {})
    root = data.get("root", "")
    root_meaning = data.get("root_meaning", "")
    arabic = data.get("arabic", "")

if st.button("Generate Mnemonic & Image"):
    if term and root and root_meaning and arabic:
        story = generate_mnemonic(term, root, root_meaning)
        st.subheader("Mnemonic Story")
        st.write(story)
        
        st.subheader("Visual Illustration")
        if api_choice == "DALL-E (OpenAI)":
            image_url = generate_image_dalle(story, root, term)
        elif api_choice == "Ideogram":
            image_url = generate_image_ideogram(story, root, term)
        else:  # Google
            image_url = generate_image_google(story, root, term)
        
        if image_url:
            if image_url.startswith("data:image"):  # Base64 handling
                st.image(image_url)
            else:
                response = requests.get(image_url)
                img = Image.open(io.BytesIO(response.content))
                st.image(img, caption=f"Generated for {term} via {api_choice}")
        
        st.subheader("Pronunciation (with Tashkeel)")
        voweled = add_tashkeel(arabic)
        st.write(voweled)
        
        # TTS Audio
        tts = gtts.gTTS(voweled, lang='ar')
        tts.save("audio.mp3")
        st.audio("audio.mp3")
    else:
        st.error("Fill in all fields!")

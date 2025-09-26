import streamlit as st
import requests
import json
import google.generativeai as genai
from gtts import gTTS
from PIL import Image
import io
import os
from datetime import datetime
import base64

# Configure the page
st.set_page_config(
    page_title="Time Travel Chatbot",
    page_icon="🕰️",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .story-container {
        background-color: #f0f2f6;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: #000000;
        line-height: 1.6;
    }
    .stExpander {
        color: #000000;
    }
    .kb-badge {
        background-color: #28a745;
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin-left: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'generated_content' not in st.session_state:
    st.session_state.generated_content = None
if 'events_data' not in st.session_state:
    st.session_state.events_data = None
if 'selected_year' not in st.session_state:
    st.session_state.selected_year = None
if 'source' not in st.session_state:
    st.session_state.source = None

# Title and description
st.markdown('<div class="main-header">🕰️ Time Travel Chatbot</div>', unsafe_allow_html=True)
st.markdown("### Journey through history with AI-generated stories, images, and audio!")

# Hardcoded API Keys
perplexity_api_key = "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"
gemini_api_key = "AIzaSyAxLvKFf2ivsR5wckVyW7PacMn_ai1wLzs"
stability_api_key = "sk-UJwptXy73hnck1WyZWThNAKDqExo6QR3vZSktg5dv4HgKW9X"

# KNOWLEDGE BASE CONFIGURATION
KNOWLEDGE_BASE_FILE = "knowledge_base.json"
KNOWLEDGE_BASE_START_YEAR = 2015
KNOWLEDGE_BASE_END_YEAR = 2024

def load_knowledge_base():
    """Load events from the knowledge base JSON file"""
    try:
        with open(KNOWLEDGE_BASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"❌ Knowledge base file '{KNOWLEDGE_BASE_FILE}' not found.")
        return []
    except json.JSONDecodeError:
        st.error(f"❌ Error parsing knowledge base file.")
        return []

def get_events_from_knowledge_base(year):
    """Get events for a specific year from the knowledge base - FIXED FOR YOUR FORMAT"""
    kb_events = load_knowledge_base()
    
    # Filter events for the specific year
    year_events = [event for event in kb_events if event["year"] == int(year)]
    
    # Convert YOUR knowledge base format to the app's expected format
    formatted_events = []
    for event in year_events:
        formatted_event = {
            "event": event["event"],
            "date": event["date"],
            "significance": f"Major historical event from {year}",
            "perspectives": list(event["perspectives"].keys())  # Extract perspective names from dict keys
        }
        formatted_events.append(formatted_event)
    
    return formatted_events

def should_use_knowledge_base(year):
    """Check if the year falls within the knowledge base range"""
    try:
        year_int = int(year)
        return KNOWLEDGE_BASE_START_YEAR <= year_int <= KNOWLEDGE_BASE_END_YEAR
    except ValueError:
        return False

def get_historical_events(year, api_key):
    """Smart event fetcher - uses KB for recent years, Perplexity for older years"""
    
    # Check if we should use knowledge base
    if should_use_knowledge_base(year):
        kb_events = get_events_from_knowledge_base(year)
        if kb_events:
            st.session_state.source = "knowledge_base"
            st.success(f"📚 Loaded from Knowledge Base ({len(kb_events)} events)")
            return kb_events
        else:
            st.warning(f"ℹ️ No events found in knowledge base for {year}, falling back to Perplexity AI")
    
    # Fall back to Perplexity AI for years outside KB range or if KB has no data
    st.session_state.source = "perplexity"
    return get_events_from_perplexity(year, api_key)

def get_events_from_perplexity(year, api_key):
    """Fetch historical events using Perplexity AI (for years outside KB)"""
    url = "https://api.perplexity.ai/chat/completions"
    
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": """You are a expert historian. Extract 3-5 major historical events for the given year. 
                For each event, suggest 4 interesting perspectives from which to experience the event.
                Return ONLY valid JSON in this exact format:
                {
                    "events": [
                        {
                            "event": "Event name",
                            "date": "Specific date if known", 
                            "significance": "Brief significance",
                            "perspectives": ["Perspective 1", "Perspective 2", "Perspective 3", "Perspective 4"]
                        }
                    ]
                }"""
            },
            {
                "role": "user",
                "content": f"What were the major globally significant historical events in {year}? Focus on events that had wide impact."
            }
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
        "search_mode": "web",
        "return_related_questions": False
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Clean the response and parse JSON
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        
        data = json.loads(content)
        events = data.get('events', [])
        st.success(f"🔍 Fetched from Perplexity AI ({len(events)} events)")
        return events
        
    except Exception as e:
        st.error(f"❌ Error fetching historical events: {str(e)}")
        return get_fallback_events(year)

def get_fallback_events(year):
    """Fallback events if both KB and API fail"""
    fallback_events = {
        "1947": [
            {
                "event": "India's Independence",
                "date": "August 15, 1947",
                "significance": "India gained independence from British rule",
                "perspectives": ["Freedom Fighter", "British Soldier", "Local Merchant", "Journalist"]
            }
        ],
        "1969": [
            {
                "event": "Apollo 11 Moon Landing",
                "date": "July 20, 1969",
                "significance": "First humans walked on the moon",
                "perspectives": ["Astronaut", "Mission Control Engineer", "TV Viewer", "Scientist"]
            }
        ]
    }
    
    return fallback_events.get(year, [
        {
            "event": f"Major Historical Events of {year}",
            "date": year,
            "significance": "Significant events that shaped history during this period",
            "perspectives": ["Witness", "Participant", "Historian", "Journalist"]
        }
    ])

def generate_story(event, perspective, year, gemini_api_key):
    """Generate historical story - uses KB if available, otherwise Gemini"""
    
    # Fall back to Gemini AI for stories not in KB
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        Write an immersive, first-person historical narrative from the perspective of a {perspective} 
        experiencing the event: "{event['event']}" in the year {year}.
        
        Requirements:
        - Write in first-person perspective as if the reader IS the {perspective}
        - Make it emotionally engaging and historically plausible
        - Include sensory details (sights, sounds, smells)
        - Length: 300-400 words
        - Focus on the human experience and emotions
        - Historical accuracy is important
        
        Event context: {event.get('significance', '')}
        """
        
        response = model.generate_content(prompt)
        st.info("🤖 Generated new story using Gemini AI")
        return response.text
        
    except Exception as e:
        st.error(f"❌ Story generation failed: {str(e)}")
        return f"""**Story from {perspective} perspective:**

As a {perspective}, I found myself at the heart of {event['event']} in {year}. {event.get('significance', 'This moment would echo through time, shaping the world in ways we could scarcely imagine.')}"""

def generate_image(event, perspective, year, api_key):
    """Generate historical image using Stability AI"""
    try:
        url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
        
        prompt = f"Historical scene: {event['event']} in {year} from {perspective} perspective. Photorealistic, authentic historical details, dramatic lighting, cinematic quality."
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Accept': 'image/*'
        }
        
        data = {
            'prompt': prompt,
            'output_format': 'webp',
        }
        
        response = requests.post(url, headers=headers, files={'none': ''}, data=data, timeout=30)
        response.raise_for_status()
        
        return response.content
        
    except Exception as e:
        st.error(f"❌ Image generation failed: {str(e)}")
        return None

def generate_audio(story_text):
    """Generate audio from story text using gTTS"""
    try:
        if len(story_text) > 4000:
            story_text = story_text[:4000] + "... [story continues]"
        
        tts = gTTS(text=story_text, lang='en', slow=False)
        audio_file = f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        tts.save(audio_file)
        return audio_file
        
    except Exception as e:
        st.error(f"❌ Audio generation failed: {str(e)}")
        return None

def display_events_interface(events, year, perplexity_api_key, gemini_api_key, stability_api_key):
    """Display events and perspectives for user selection"""
    
    # Show data source badge
    source_badge = "📚 Knowledge Base" if st.session_state.source == "knowledge_base" else "🔍 Perplexity AI"
    st.markdown(f"### 📜 Major Historical Events in {year} <span class='kb-badge'>{source_badge}</span>", unsafe_allow_html=True)
    
    # Create event selection
    event_options = [f"{i+1}. {event['event']} ({event.get('date', 'Date unknown')})" 
                    for i, event in enumerate(events)]
    
    selected_event_str = st.selectbox("Choose an event:", event_options, key="event_selector")
    event_index = int(selected_event_str.split('.')[0]) - 1
    selected_event = events[event_index]
    
    # Display event significance
    st.info(f"**Significance:** {selected_event['significance']}")
    
    # Perspective selection
    st.markdown("### 👥 Choose Your Perspective")
    perspective = st.selectbox("Experience the event through the eyes of:", 
                              selected_event['perspectives'], key="perspective_selector")
    
    # Generate button
    if st.button("✨ Generate Time Travel Experience", use_column_width=True, key="generate_btn"):
        with st.spinner("🚀 Creating your time travel experience..."):
            # Generate story (will use KB if available)
            story = generate_story(selected_event, perspective, year, gemini_api_key)
            if not story:
                st.error("❌ Failed to generate story")
                return
            
            # Generate image
            image_bytes = generate_image(selected_event, perspective, year, stability_api_key)
            
            # Generate audio
            audio_file = generate_audio(story)
            
            # Store in session state
            st.session_state.generated_content = {
                'event': selected_event,
                'perspective': perspective,
                'year': year,
                'story': story,
                'image_bytes': image_bytes,
                'audio_file': audio_file,
                'source': st.session_state.source
            }
            
            st.rerun()

def display_generated_content():
    """Display the generated story, image, and audio"""
    content = st.session_state.generated_content
    
    st.markdown("---")
    st.markdown("## 🎭 Your Time Travel Experience")
    
    # Display event info with source badge
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"### 📅 {content['year']}: {content['event']['event']}")
        st.markdown(f"**👤 Perspective:** {content['perspective']}")
    
    with col2:
        st.markdown(f"**📅 Date:** {content['event'].get('date', 'Historical period')}")
    
    with col3:
        source_badge = "📚 KB" if content.get('source') == "knowledge_base" else "🔍 AI"
        st.markdown(f"**Source:** {source_badge}")
    
    # Display image
    if content['image_bytes']:
        st.markdown("### 🖼️ Generated Historical Scene")
        try:
            image = Image.open(io.BytesIO(content['image_bytes']))
            st.image(image, use_column_width=True, caption=f"{content['event']['event']} - {content['perspective']} perspective")
        except Exception as e:
            st.error(f"❌ Error displaying image: {str(e)}")
    
    # Display story
    st.markdown("### 📖 Your Story")
    with st.expander("Read the full story", expanded=True):
        st.markdown(f'<div class="story-container">{content["story"]}</div>', unsafe_allow_html=True)
    
    # Audio player
    if content['audio_file'] and os.path.exists(content['audio_file']):
        st.markdown("### 🔊 Listen to the Story")
        with open(content['audio_file'], "rb") as audio_file:
            audio_bytes = audio_file.read()
        st.audio(audio_bytes, format='audio/mp3')
    
    # New journey button
    st.markdown("---")
    if st.button("🕰️ Start New Time Travel Journey", use_container_width=True):
        # Cleanup audio file
        if (st.session_state.generated_content.get('audio_file') and 
            os.path.exists(st.session_state.generated_content['audio_file'])):
            os.remove(st.session_state.generated_content['audio_file'])
        
        # Reset session state
        st.session_state.generated_content = None
        st.session_state.events_data = None
        st.session_state.selected_year = None
        st.session_state.source = None
        st.rerun()

# Main app functionality
def main():
    # API key validation
    if not all([perplexity_api_key, gemini_api_key, stability_api_key]):
        st.error("❌ Please update the API keys in the code with your actual API keys")
        return
    
    # Year input with knowledge base info
    st.markdown("---")
    
    # Knowledge base info
    with st.expander("ℹ️ About the Knowledge Base", expanded=False):
        st.info(f"""
        **Knowledge Base Coverage:** {KNOWLEDGE_BASE_START_YEAR} - {KNOWLEDGE_BASE_END_YEAR}
        
        - 📚 **Years {KNOWLEDGE_BASE_START_YEAR}-{KNOWLEDGE_BASE_END_YEAR}**: Loaded from local knowledge base
        - 🔍 **Other years**: Fetched from Perplexity AI
        - 📖 **Stories**: Use pre-written content when available, otherwise generated by AI
        """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        year_input = st.text_input("📅 Enter the year you want to visit:", 
                                  placeholder="e.g., 2020, 1969, 1776...",
                                  key="year_input")
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_clicked = st.button("🔍 Search Historical Events", use_column_width=True, key="search_btn")
    
    # Store events in session state to prevent re-fetching
    if search_clicked and year_input:
        if not year_input.isdigit():
            st.error("❌ Please enter a valid year (numbers only)")
            return
        
        with st.spinner("🕵️‍♂️ Searching for major historical events..."):
            events = get_historical_events(year_input, perplexity_api_key)
        
        if events:
            st.session_state.events_data = events
            st.session_state.selected_year = year_input
            st.rerun()
        else:
            st.error("❌ No historical events found for this year. Try another year!")
    
    # Display events interface if we have data
    if st.session_state.events_data and st.session_state.selected_year:
        display_events_interface(
            st.session_state.events_data, 
            st.session_state.selected_year,
            perplexity_api_key,
            gemini_api_key, 
            stability_api_key
        )
    
    # Display generated content if available
    if st.session_state.generated_content:
        display_generated_content()

# Run the app
if __name__ == "__main__":
    main()



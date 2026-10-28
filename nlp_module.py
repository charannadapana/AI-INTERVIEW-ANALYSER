import speech_recognition as sr
from textblob import TextBlob
import re
import math
import collections

def compute_tf(text):
    words = text.lower().split()
    tf = collections.Counter(words)
    total = len(words)
    for word in tf:
        tf[word] = tf[word] / total
    return tf, words

def _cosine_similarity(vec1, vec2):
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])
    sum1 = sum([vec1[x]**2 for x in vec1.keys()])
    sum2 = sum([vec2[x]**2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    return float(numerator) / denominator if denominator else 0.0

def calculate_relevance(expected, transcript):
    if not expected or not transcript: return 0.0
    tf_exp, w_exp = compute_tf(expected)
    tf_trans, w_trans = compute_tf(transcript)
    
    # idf approximation: if word is in both it has idf=log(2/2)=0, meaning tf-idf approach with 2 docs only cares about overlap tf.
    # We will just use TF vector cosine similarity
    score = _cosine_similarity(tf_exp, tf_trans)
    return round(score * 10, 2)

def convert_audio_to_text(audio_path):
    """ Converts a WAV audio file to text using Google Speech Recognition. """
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        print(f"Error in speech to text: {e}")
        return ""

def analyze_response(transcript, expected_answer, required_skills):
    if not transcript:
        return [], 0.0, "unknown", 0.0, 0.0, 0
        
    # 0. Filler Word Detection
    filler_words = ["um", "uh", "ah", "like", "basically", "you know", "kinda", "sorta", "literally"]
    transcript_lower = transcript.lower()
    
    filler_count = 0
    for fw in filler_words:
        # Regex count exact word matches for fillers
        matches = len(re.findall(r'\b' + re.escape(fw) + r'\b', transcript_lower))
        filler_count += matches

    # 1. Relevance Score
    relevance_score = calculate_relevance(expected_answer, transcript)
    relevance_score = min(relevance_score + 1.5, 10.0) if relevance_score > 0.1 else relevance_score
    relevance_score = round(relevance_score, 2)
    
    # 2. Keyword / Skill Detection
    skills_list = [skill.strip().lower() for skill in required_skills.split(",")]
    transcript_lower = transcript.lower()
    detected_skills = []
    for skill in skills_list:
        if re.search(r'\b' + re.escape(skill) + r'\b', transcript_lower):
            detected_skills.append(skill.upper())
    
    # 3. Sentiment Analysis (for Tone/Confidence)
    blob = TextBlob(transcript)
    polarity = blob.sentiment.polarity
    if polarity > 0.3:
        tone = "confident"
        confidence_score = 8.0 + (polarity * 2.0)
    elif polarity < -0.1:
        tone = "nervous"
        confidence_score = 4.0 + (polarity * 2.0)
    else:
        tone = "neutral"
        confidence_score = 6.0 + (polarity * 2.0)
        
    confidence_score = round(max(0.0, min(10.0, confidence_score)), 2)

    # 4. Communication Quality
    sentences = len(blob.sentences) if len(blob.sentences) > 0 else 1
    words = len(blob.words)
    avg_words_per_sentence = words / sentences
    
    comm_score = 5.0
    if 8 <= avg_words_per_sentence <= 25:
        comm_score += 3.0
    elif avg_words_per_sentence < 8:
        comm_score += 1.0 
    else:
        comm_score += 1.0 
        
    # Deduct communication for excessive filler words
    if filler_count > 3:
        comm_score -= min((filler_count - 3) * 0.5, 3.0)
        
    if len(transcript.strip()) > 30:
        comm_score += 2.0
    
    comm_score = round(max(0.0, min(10.0, comm_score)), 2)
    
    return detected_skills, relevance_score, tone, confidence_score, comm_score, filler_count

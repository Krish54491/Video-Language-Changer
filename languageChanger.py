import cv2
import moviepy as mp
import numpy as np
import os
import speech_recognition as sr
import re
from openai import OpenAI
from flask import Flask, request, redirect, url_for, render_template_string, send_file
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import gtts.lang

app = Flask(__name__)
transcript = ""
translated_transcript = ""
aiComment = ""
transcribedCount = 0
language = "Spanish"  # Desired language for translation
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

language_map = {
    'ca': 'Catalan',
    'cs': 'Czech', 
    'cy': 'Welsh', 
    'da': 'Danish', 
    'de': 'German', 
    'el': 'Greek', 
    'en': 'English', 
    'es': 'Spanish', 
    'et': 'Estonian', 
    'eu': 'Basque', 
    'fi': 'Finnish', 
    'fr': 'French', 
    'fr-CA': 'French (Canada)', 
    'gl': 'Galician', 
    'gu': 'Gujarati', 
    'ha': 'Hausa',
    'hi': 'Hindi',
    'hr': 'Croatian',
    'hu': 'Hungarian',
    'id': 'Indonesian',
    'is': 'Icelandic',
    'it': 'Italian',
    'iw': 'Hebrew',
    'ja': 'Japanese',
    'jw': 'Javanese',
    'km': 'Khmer',
    'kn': 'Kannada',
    'ko': 'Korean',
    'la': 'Latin',
    'lt': 'Lithuanian',
    'lv': 'Latvian',
    'ml': 'Malayalam',
    'mr': 'Marathi',
    'ms': 'Malay',
    'my': 'Myanmar (Burmese)',
    'ne': 'Nepali',
    'nl': 'Dutch',
    'no': 'Norwegian',
    'pa': 'Punjabi (Gurmukhi)',
    'pl': 'Polish',
    'pt': 'Portuguese (Brazil)',
    'pt-PT': 'Portuguese (Portugal)',
    'ro': 'Romanian',
    'ru': 'Russian',
    'si': 'Sinhala',
    'sk': 'Slovak',
    'sq': 'Albanian',
    'sr': 'Serbian',
    'su': 'Sundanese',
    'sv': 'Swedish',
    'sw': 'Swahili',
    'ta': 'Tamil',
    'te': 'Telugu',
    'th': 'Thai',
    'tl': 'Filipino',
    'tr': 'Turkish',
    'uk': 'Ukrainian',
    'ur': 'Urdu',
    'vi': 'Vietnamese',
    'yue': 'Cantonese',
    'zh-CN': 'Chinese (Simplified)',
    'zh-TW': 'Chinese (Mandarin/Taiwan)',
    'zh': 'Chinese (Mandarin)'
}

# Reverse map (value → key)
reverse_language_map = {v.lower(): k for k, v in language_map.items()}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# print("This program will rate a video using AI to rate a transcript of the video. \nThen will rate the visuals on how blurry it is and the audio on how clear it is")

def extract_audio(video_path, audio_path="temp_audio.wav"):
    global transcript
    global translated_transcript
    global transcribedCount
    video = mp.VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)

    r = sr.Recognizer()
    with sr.AudioFile("temp_audio.wav") as source:
        totalDuration = int(source.DURATION)
        chunkDuration = 10 # change this to change how long it listens before transcribing (less is recommended) the shorter it is the longer the rating will take
        # print(f"Audio duration: {totalDuration:.2f} sec")
        for i in range(0, totalDuration, chunkDuration):
            # print(f"Transcribing chunk {i}–{i+chunkDuration} seconds...")
            transcribedCount += 1
            try:
                audio = r.record(source,duration=chunkDuration)
                text = r.recognize_google(audio)
                transcript += text
                segment = get_translation(text)
                translated_transcript += segment + " time stamp: " + str(i) + " to " + str(min(i+chunkDuration, totalDuration)) + "\n"
                with open("transcription.txt", "w") as f:
                    f.write(transcript)
                with open("translated_transcription.txt", "w", encoding="utf-8") as f:
                    f.write(translated_transcript)
            except sr.UnknownValueError:
                print("Could not understand audio")

            except sr.RequestError as e:
                print("Could not request results from Google Speech Recognition service; {0}".format(e))
        video.audio.close()
        video.close()
        return audio_path

# cheap function that translates all at once, but worse
def get_translation():
    if(not transcript):
       return -1
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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", #feel free to use this key, it has a dollar limit on it doesn't matter if you use it
    )
    completion = client.chat.completions.create(
        model="deepseek/deepseek-chat-v3.1:free",
        messages=
        [
          {
            "role": "user",
            "content": ("Hello your job is to translate this transcript to " + language + "Transcript:" + transcript)
            }
        ]
    )

    try:
        global aiComment
        aiComment = completion.choices[0].message.content
        print(completion.choices[0].message.content)
    except Exception as e:
        print("Error during AI completion:", e)
        return -1
    try:
        with open("translated_transcription.txt", "w", encoding="utf-8") as f:
            f.write(aiComment)
    except Exception as e:
        print("Error saving translated transcript:", e)
    return aiComment

# this is the more expensive function that translates in segments
def get_translation(segment):
    if(not transcript):
       return -1
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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", #feel free to use this key, it has a dollar limit on it doesn't matter if you use it
    )
    completion = client.chat.completions.create(
        model="deepseek/deepseek-chat-v3.1:free",
        messages=
        [
          {
            "role": "user",
            "content": ("Hello your job is to translate this transcript to " + language + "Don't add any extra comments or texts as this will be used for tts. Segment:" + segment)
            }
        ]
    )

    try:
        global aiComment
        aiComment += completion.choices[0].message.content
        segment = completion.choices[0].message.content
        print(segment)
    except Exception as e:
        print("Error during AI completion:", e)
        return -1
    return segment
@app.route('/download-transcript')
def download_transcript():
    transcript_path = "transcription.txt"
    if os.path.exists(transcript_path):
        return send_file(transcript_path, as_attachment=True)
    else:
        return "Transcript not found.", 404

@app.route('/download-translated-transcript')
def download_translated_transcript():
    transcript_path = "translated_transcription.txt"
    if os.path.exists(transcript_path):
        return send_file(transcript_path, as_attachment=True)
    else:
        return "Transcript not found.", 404
@app.route("/translate")
def translate_video(video_path, target_language):
    global language
    if target_language:
        language = target_language
    extract_audio(video_path)
    result = f"<h2>Translation Result:</h2><p>{aiComment}</p>"
    return result

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def upload_video():
    if request.method == "POST":
        if 'video' not in request.files:
            return "No file part"
        file = request.files['video']
        if file.filename == '':
            return "No selected file"
        if file and allowed_file(file.filename):
            video_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(video_path)
            # Read selected target language from the form and call translate
            selected_language = request.form.get('language')
            global aiComment
            aiComment = ""
            result = translate_video(video_path, selected_language)
            return '''
            <!doctype html>
            <html>
            <head>
            <title>AI Video Translator</title>
            <script>
              // Hide progress message after rating is done
              window.onload = function() {
                document.getElementById('language').classList.add('select2');
                $('.select2').select2({
                    placeholder: "Choose a language",
                    allowClear: true
                });
                document.getElementById('progress').style.display = 'none';
              };
            </script>
            </head>
            <body>
            <h1>AI Video Translator</h1>
            <p>The default language to translate to is Spanish. The AI is not perfect and may not always provide accurate translations.</p>
            <form method=post enctype=multipart/form-data onsubmit="document.getElementById('progress').style.display='block';">
                            <label for="language">Choose target language:</label>
                            <select name="language" id="language">
                                <option value="English">English</option>
                                <option value="Catalan">Catalan</option>
                                <option value="Czech">Czech</option>
                                <option value="Welsh">Welsh</option>
                                <option value="Danish">Danish</option>
                                <option value="German">German</option>
                                <option value="Spanish">Spanish</option>
                                <option value="Greek">Greek</option>
                                <option value="Estonian">Estonian</option>
                                <option value="Basque">Basque</option>
                                <option value="Finnish">Finnish</option>
                                <option value="French">French</option>
                                <option value="Galician">Galician</option>
                                <option value="Gujarati">Gujarati</option>
                                <option value="Hausa">Hausa</option>
                                <option value="Croatian">Croatian</option>
                                <option value="Hungarian">Hungarian</option>
                                <option value="Indonesian">Indonesian</option>
                                <option value="Icelandic">Icelandic</option>
                                <option value="Italian">Italian</option>
                                <option value="Hebrew">Hebrew</option>
                                <option value="Japanese">Japanese</option>
                                <option value="Javanese">Javanese</option>
                                <option value="Khmer">Khmer</option>
                                <option value="Kannada">Kannada</option>
                                <option value="Korean">Korean</option>
                                <option value="Latin">Latin</option>
                                <option value="Lithuanian">Lithuanian</option>
                                <option value="Latvian">Latvian</option>
                                <option value="Malayalam">Malayalam</option>
                                <option value="Marathi">Marathi</option>
                                <option value="Malay">Malay</option>
                                <option value="Hindi">Hindi</option>
                                <option value="Myanmar (Burmese)">Myanmar (Burmese)</option>
                                <option value="Nepali">Nepali</option>
                                <option value="Dutch">Dutch</option>
                                <option value="Norwegian">Norwegian</option>
                                <option value="Punjabi (Gurmukhi)">Punjabi (Gurmukhi)</option>
                                <option value="Polish">Polish</option>
                                <option value="Portuguese (Brazil)">Portuguese (Brazil)</option>
                                <option value="Portuguese (Portugal)">Portuguese (Portugal)</option>
                                <option value="Romanian">Romanian</option>
                                <option value="Russian">Russian</option>
                                <option value="Sinhala">Sinhala</option>
                                <option value="Slovak">Slovak</option>
                                <option value="Albanian">Albanian</option>
                                <option value="Serbian">Serbian</option>
                                <option value="Sundanese">Sundanese</option>
                                <option value="Swedish">Swedish</option>
                                <option value="Swahili">Swahili</option>
                                <option value="Tamil">Tamil</option>
                                <option value="Telugu">Telugu</option>
                                <option value="Thai">Thai</option>
                                <option value="Filipino">Filipino</option>
                                <option value="Turkish">Turkish</option>
                                <option value="Ukrainian">Ukrainian</option>
                                <option value="Urdu">Urdu</option>
                                <option value="Vietnamese">Vietnamese</option>
                                <option value="Cantonese">Cantonese</option>
                                <option value="Chinese (Simplified)">Chinese (Simplified)</option>
                                <option value="Chinese (Mandarin/Taiwan)">Chinese (Mandarin/Taiwan)</option>
                            </select>
                            <br/>
                            <input type=file name=video accept="video/*" required>
              <input type=submit value=Upload>
            </form>
            <div id="progress" style="color:blue; font-weight:bold; display:none;">
              Video Translating in Progress...
            </div>''' + result + '''
            <p><a href="/download-transcript" download>
               <button type="button">Download Transcribed Transcript</button>
            </a></p>
            <p><a href="/download-translated-transcript" download>
               <button type="button">Download Translated Transcript</button>
            </a></p>
            <p><a href="/generate-audio" download>
               <button type="button">Download Audio</button>
            </a></p>
            </body>
            </html>
            '''
        else:
            return "Invalid file type. Please upload a video file."
    return '''
    <!doctype html>
    <html>
    <head>
    <title>AI Video Translator</title>
    <script>
      function showProgress() {
        document.getElementById('progress').style.display = 'block';
        document.getElementById('language').classList.add('select2');
            $('.select2').select2({
                placeholder: "Choose a language",
                allowClear: true
            });
      }
    </script>
    </head>
    <body>
    <h1>AI Video Translator</h1>
    <p>The default language to translate to is Spanish. The AI is not perfect and may not always provide accurate translations.</p>
        <form method=post enctype=multipart/form-data onsubmit="showProgress()">
            <label for="language">Choose target language:</label>
            <select name="language" id="language">
                <option value="English">English</option>
                <option value="Catalan">Catalan</option>
                <option value="Czech">Czech</option>
                <option value="Welsh">Welsh</option>
                <option value="Danish">Danish</option>
                <option value="German">German</option>
                <option value="Spanish">Spanish</option>
                <option value="Greek">Greek</option>
                <option value="Estonian">Estonian</option>
                <option value="Basque">Basque</option>
                <option value="Finnish">Finnish</option>
                <option value="French">French</option>
                <option value="Galician">Galician</option>
                <option value="Gujarati">Gujarati</option>
                <option value="Hausa">Hausa</option>
                <option value="Croatian">Croatian</option>
                <option value="Hungarian">Hungarian</option>
                <option value="Indonesian">Indonesian</option>
                <option value="Icelandic">Icelandic</option>
                <option value="Italian">Italian</option>
                <option value="Hebrew">Hebrew</option>
                <option value="Japanese">Japanese</option>
                <option value="Javanese">Javanese</option>
                <option value="Khmer">Khmer</option>
                <option value="Kannada">Kannada</option>
                <option value="Korean">Korean</option>
                <option value="Latin">Latin</option>
                <option value="Lithuanian">Lithuanian</option>
                <option value="Latvian">Latvian</option>
                <option value="Malayalam">Malayalam</option>
                <option value="Marathi">Marathi</option>
                <option value="Malay">Malay</option>
                <option value="Hindi">Hindi</option>
                <option value="Myanmar (Burmese)">Myanmar (Burmese)</option>
                <option value="Nepali">Nepali</option>
                <option value="Dutch">Dutch</option>
                <option value="Norwegian">Norwegian</option>
                <option value="Punjabi (Gurmukhi)">Punjabi (Gurmukhi)</option>
                <option value="Polish">Polish</option>
                <option value="Portuguese (Brazil)">Portuguese (Brazil)</option>
                <option value="Portuguese (Portugal)">Portuguese (Portugal)</option>
                <option value="Romanian">Romanian</option>
                <option value="Russian">Russian</option>
                <option value="Sinhala">Sinhala</option>
                <option value="Slovak">Slovak</option>
                <option value="Albanian">Albanian</option>
                <option value="Serbian">Serbian</option>
                <option value="Sundanese">Sundanese</option>
                <option value="Swedish">Swedish</option>
                <option value="Swahili">Swahili</option>
                <option value="Tamil">Tamil</option>
                <option value="Telugu">Telugu</option>
                <option value="Thai">Thai</option>
                <option value="Filipino">Filipino</option>
                <option value="Turkish">Turkish</option>
                <option value="Ukrainian">Ukrainian</option>
                <option value="Urdu">Urdu</option>
                <option value="Vietnamese">Vietnamese</option>
                <option value="Cantonese">Cantonese</option>
                <option value="Chinese (Simplified)">Chinese (Simplified)</option>
                <option value="Chinese (Mandarin/Taiwan)">Chinese (Mandarin/Taiwan)</option>
            /select>
            <br/>
            <input type=file name=video accept="video/*" required>
            <input type=submit value=Upload>
        </form>
    
    <div id="progress" style="color:blue; font-weight:bold; display:none;">
      Video Translating in Progress...
    </div>
    </body>
    </html>
    '''

def generate_audio_from_transcript(output_file="output_audio.mp3"):
    """
    Generate an audio file from the translated transcript.
    Each segment of the transcript is read by an AI voice and ends at the specified timestamp.
    """
    global language
    segments = translated_transcript.split("\n")
    audio_segments = []
    for segment in segments:
        if "time stamp:" in segment:
            try:
                text, timestamp = segment.rsplit("time stamp:", 1)
                start, end = map(int, timestamp.split("to"))
                lang = reverse_language_map.get(language.lower(), "en")
                # Generate TTS audio for the text
                tts = gTTS(text=text.strip(), lang=lang)
                tts.save("temp_segment.mp3")

                # Load the audio and adjust duration to match the timestamp
                audio = AudioSegment.from_file("temp_segment.mp3")
                duration = (end - start) * 1000  # Convert seconds to milliseconds
                audio = audio[:duration]  # Trim or pad audio to match duration

                audio_segments.append(audio)
            except Exception as e:
                print(f"Error processing segment: {segment}. Error: {e}")

    # Combine all audio segments
    if audio_segments:
        final_audio = sum(audio_segments)
        final_audio.export(output_file, format="mp3")
        print(f"Audio file generated: {output_file}")
        return output_file
    else:
        print("No audio segments generated.")
        return None

@app.route('/generate-audio', methods=['GET'])
def generate_audio():
    """Endpoint to generate and download the audio file."""
    if not translated_transcript.strip():
        return "Transcript is empty. Cannot generate audio.", 400

    audio_file = generate_audio_from_transcript()
    if audio_file:
        return send_file(audio_file, as_attachment=True)
    else:
        return "Failed to generate audio file.", 500

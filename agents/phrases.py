"""Offline phrasing, in the learner's language.

The mock provider must behave like the real one where it matters: answer in
the right language, refuse when the lesson does not cover the question, and
never pretend to be a model. These strings are what makes that possible with
no API key — and they are also what the live path falls back to on an error.
"""

from __future__ import annotations

PHRASES: dict[str, dict[str, str]] = {
    "from_lesson": {
        "en-IN": "From the lesson:",
        "hi-IN": "पाठ से:",
        "bn-IN": "পাঠ থেকে:",
        "ta-IN": "பாடத்திலிருந்து:",
        "te-IN": "పాఠం నుండి:",
    },
    "refusal": {
        "en-IN": "That is not covered in the lesson you are reading, so I will not guess.",
        "hi-IN": "आप जो पाठ पढ़ रहे हैं उसमें यह नहीं है, इसलिए मैं अनुमान नहीं लगाऊँगा।",
        "bn-IN": "আপনি যে পাঠটি পড়ছেন, তাতে এটা নেই, তাই আমি অনুমান করব না।",
        "ta-IN": "நீங்கள் படிக்கும் பாடத்தில் அது இடம்பெறவில்லை, அதனால் நான் யூகிக்கப் போவதில்லை.",
        "te-IN": "మీరు చదువుతున్న పాఠంలో అది లేదు, కాబట్టి నేను ఊహించను.",
    },
    "hint": {
        "en-IN": "Hint: read again the part about",
        "hi-IN": "संकेत: इसके बारे में वाला भाग फिर पढ़िए —",
        "bn-IN": "ইঙ্গিত: যে অংশটি সম্পর্কে বলা হয়েছে, সেটি আবার পড়ুন —",
        "ta-IN": "குறிப்பு: இதைப் பற்றிய பகுதியை மீண்டும் படிக்கவும் —",
        "te-IN": "సూచన: దీని గురించిన భాగాన్ని మళ్లీ చదవండి —",
    },
    "followup": {
        "en-IN": "Can you tell me in one sentence what you understood?",
        "hi-IN": "आपने क्या समझा, एक वाक्य में बता सकते हैं?",
        "bn-IN": "আপনি কী বুঝেছেন, সেটা কি আমাকে এক বাক্যে বলতে পারবেন?",
        "ta-IN": "உங்களுக்குப் புரிந்தது என்ன என்பதை ஒரே வாக்கியத்தில் சொல்ல முடியுமா?",
        "te-IN": "మీకు అర్థమైనదాన్ని ఒకే వాక్యంలో చెప్పగలరా?",
    },
    "mock_note": {
        "en-IN": "Mock mode — this is a canned answer, not a model reply.",
        "hi-IN": "मॉक मोड — यह पहले से लिखा उत्तर है, मॉडल का उत्तर नहीं।",
        "bn-IN": "মক মোড — এটি একটি আগে থেকে দেওয়া উত্তর, মডেলের উত্তর নয়।",
        "ta-IN": "மாக் முறை — இது முன்பே எழுதப்பட்ட பதில், மாடலின் பதில் அல்ல.",
        "te-IN": "మాక్ మోడ్ — ఇది ముందుగా రాసి ఉంచిన సమాధానం, మోడల్ రిప్లై కాదు.",
    },
    "ask_title": {
        "en-IN": "Ask the tutor",
        "hi-IN": "शिक्षक से पूछें",
        "bn-IN": "শিক্ষককে জিজ্ঞাসা করুন",
        "ta-IN": "பயிற்சியாளரிடம் கேளுங்கள்",
        "te-IN": "ట్యూటర్‌ని అడగండి",
    },
    "ask_button": {
        "en-IN": "Ask",
        "hi-IN": "पूछें",
        "bn-IN": "জিজ্ঞাসা করুন",
        "ta-IN": "கேளுங்கள்",
        "te-IN": "అడగండి",
    },
    "simpler": {
        "en-IN": "Explain simpler",
        "hi-IN": "और आसान शब्दों में समझाएँ",
        "bn-IN": "সহজ করে বুঝিয়ে বলুন",
        "ta-IN": "இன்னும் எளிமையாக விளக்குங்கள்",
        "te-IN": "ఇంకా సులభంగా వివరించండి",
    },
    "example": {
        "en-IN": "Give me an example",
        "hi-IN": "एक उदाहरण दीजिए",
        "bn-IN": "আমাকে একটা উদাহরণ দিন",
        "ta-IN": "எனக்கு ஒரு உதாரணம் கொடுங்கள்",
        "te-IN": "నాకు ఒక ఉదాహరణ ఇవ్వండి",
    },
    "context": {
        "en-IN": "Reading context",
        "hi-IN": "पढ़ने का संदर्भ",
        "bn-IN": "পড়ার প্রেক্ষাপট",
        "ta-IN": "படிக்கும் சூழல்",
        "te-IN": "చదివే సందర్భం",
    },
    "grounded": {
        "en-IN": "Grounded in the lesson",
        "hi-IN": "पाठ पर आधारित",
        "bn-IN": "পাঠের ওপর ভিত্তি করে",
        "ta-IN": "பாடத்தை அடிப்படையாகக் கொண்டது",
        "te-IN": "పాఠం ఆధారంగా",
    },
    "outside": {
        "en-IN": "Outside the lesson",
        "hi-IN": "पाठ से बाहर",
        "bn-IN": "পাঠের বাইরে",
        "ta-IN": "பாடத்திற்கு வெளியே",
        "te-IN": "పాఠానికి బయట",
    },
}


def p(key: str, lang: str = "en-IN") -> str:
    """One phrase in one language, with an English fallback."""
    entry = PHRASES.get(key, {})
    return entry.get(lang) or entry.get("en-IN") or key

"""UI strings in the learner's language.

Keys are stable identifiers; values are per-language text. A missing
translation falls back to English, and a missing key returns the key itself
so a gap is visible on screen instead of crashing a page.
"""

from __future__ import annotations

from core import config

UI_STRINGS: dict[str, dict[str, str]] = {
    "tagline": {
        "en-IN": "Learn in the language you think in.",
        "hi-IN": "जिस भाषा में सोचते हैं, उसी में सीखिए।",
        "bn-IN": "আপনি যে ভাষায় চিন্তা করেন, সেই ভাষাতেই শিখুন।",
        "ta-IN": "நீங்கள் எந்த மொழியில் சிந்திக்கிறீர்களோ, அதே மொழியிலேயே கற்றுக்கொள்ளுங்கள்.",
        "te-IN": "మీరు ఏ భాషలో ఆలోచిస్తారో అదే భాషలో నేర్చుకోండి.",
    },
    "choose_language": {
        "en-IN": "Choose your language",
        "hi-IN": "अपनी भाषा चुनिए",
        "bn-IN": "আপনার ভাষা বেছে নিন",
        "ta-IN": "உங்கள் மொழியைத் தேர்ந்தெடுங்கள்",
        "te-IN": "మీ భాషను ఎంచుకోండి",
    },
    "hero_sub": {
        "en-IN": "Read, ask, and be assessed in your mother tongue.",
        "hi-IN": "अपनी मातृभाषा में पढ़िए, पूछिए और मूल्यांकन दीजिए।",
        "bn-IN": "মাতৃভাষায় পড়ুন, প্রশ্ন করুন এবং মূল্যায়নের মুখোমুখি হোন।",
        "ta-IN": "உங்கள் தாய்மொழியிலேயே படியுங்கள், கேளுங்கள், மற்றும் மதிப்பீடு பெறுங்கள்.",
        "te-IN": "మీ మాతృభాషలోనే చదవండి, అడగండి, అంచనా వేయించుకోండి.",
    },
    "telemetry_line": {
        "en-IN": "Everything you tap is measured, so a teacher can see what works.",
        "hi-IN": "आपका हर टैप दर्ज होता है, ताकि शिक्षक देख सकें क्या काम कर रहा है।",
        "bn-IN": "আপনি যা কিছুতে ট্যাপ করবেন তা মাপা হয়, যাতে একজন শিক্ষক বুঝতে পারেন কোনটি কাজ করছে।",
        "ta-IN": "நீங்கள் தொடும் அனைத்தும் அளவிடப்படுகிறது, எனவே எது வேலை செய்கிறது என்பதை ஒரு ஆசிரியர் பார்க்க முடியும்.",
        "te-IN": "మీరు నొక్కే ప్రతిదీ కొలుస్తారు, కాబట్టి ఏది బాగా పనిచేస్తుందో ఉపాధ్యాయుడు చూడగలరు.",
    },
    "built_for": {
        "en-IN": "Built for CDS208",
        "hi-IN": "CDS208 के लिए बनाया गया",
        "bn-IN": "CDS208-এর জন্য তৈরি করা হয়েছে",
        "ta-IN": "CDS208-க்காக உருவாக்கப்பட்டது",
        "te-IN": "CDS208 కోసం రూపొందించబడింది",
    },
    "card_reader": {
        "en-IN": "The lesson reader",
        "hi-IN": "पाठ वाचक",
        "bn-IN": "পাঠ পড়ার অংশ",
        "ta-IN": "பாடம் படிப்பவர்",
        "te-IN": "లెసన్ రీడర్",
    },
    "card_translate": {
        "en-IN": "Live translation",
        "hi-IN": "तुरंत अनुवाद",
        "bn-IN": "লাইভ ট্রান্সলেশন",
        "ta-IN": "நேரடி மொழிபெயர்ப்பு",
        "te-IN": "లైవ్ ట్రాన్స్‌లేషన్",
    },
    "card_tutor": {
        "en-IN": "The AI tutor",
        "hi-IN": "एआई शिक्षक",
        "bn-IN": "এআই টিউটর",
        "ta-IN": "AI ஆசிரியர்",
        "te-IN": "AI ట్యూటర్",
    },
    "card_progress": {
        "en-IN": "My progress",
        "hi-IN": "मेरी प्रगति",
        "bn-IN": "আমার অগ্রগতি",
        "ta-IN": "என் முன்னேற்றம்",
        "te-IN": "నా ప్రోగ్రెస్",
    },
    "card_analytics": {
        "en-IN": "Analytics",
        "hi-IN": "विश्लेषण",
        "bn-IN": "অ্যানালিটিক্স",
        "ta-IN": "பகுப்பாய்வு",
        "te-IN": "అనలిటిక్స్",
    },
    "mock_mode": {
        "en-IN": "Mock mode",
        "hi-IN": "मॉक मोड",
        "bn-IN": "মক মোড",
        "ta-IN": "போலி முறை",
        "te-IN": "మాక్ మోడ్",
    },
    "later_phase": {
        "en-IN": "Coming in a later phase",
        "hi-IN": "अगले चरण में आएगा",
        "bn-IN": "পরবর্তী ধাপে আসছে",
        "ta-IN": "பிற்காலத்தில் வரவுள்ளது",
        "te-IN": "తర్వాతి దశలో రాబోతోంది",
    },
    "nav_home": {
        "en-IN": "Home",
        "hi-IN": "मुख्य पृष्ठ",
        "bn-IN": "হোম",
        "ta-IN": "முகப்பு",
        "te-IN": "హోమ్",
    },
    "nav_translate": {
        "en-IN": "Translate",
        "hi-IN": "अनुवाद",
        "bn-IN": "অনুবাদ",
        "ta-IN": "மொழிபெயர்ப்பு",
        "te-IN": "అనువాదం",
    },
    "prog_lessons_touched": {
        "en-IN": "Lessons touched",
        "hi-IN": "पढ़े गए पाठ",
        "te-IN": "టచ్ చేసిన పాఠాలు",
        "ta-IN": "தொட்ட பாடங்கள்",
        "bn-IN": "স্পর্শ করা পাঠ",
    },
    "prog_quizzes_passed": {
        "en-IN": "Quizzes passed",
        "hi-IN": "पास की गई प्रश्नोत्तरी",
        "te-IN": "పాస్ చేసిన క్విజ్\u200cలు",
        "ta-IN": "தேர்ச்சி பெற்ற வினாடி வினாக்கள்",
        "bn-IN": "দেওয়া কুইজ",
    },
    "prog_avg_score": {
        "en-IN": "Average score",
        "hi-IN": "औसत स्कोर",
        "te-IN": "సగటు స్కోరు",
        "ta-IN": "சராசரி மதிப்பெண்",
        "bn-IN": "গড় স্কোর",
    },
    "prog_events_logged": {
        "en-IN": "Events logged",
        "hi-IN": "दर्ज घटनाएँ",
        "te-IN": "లాగ్ చేసిన ఈవెంట్\u200cలు",
        "ta-IN": "பதிவு செய்யப்பட்ட நிகழ்வுகள்",
        "bn-IN": "লগ করা ইভেন্ট",
    },
    "prog_next": {
        "en-IN": "Recommended next",
        "hi-IN": "आगे के लिए सुझाव",
        "te-IN": "తర్వాత సిఫార్సు చేసినవి",
        "ta-IN": "பரிந்துரைக்கப்படும் அடுத்தவை",
        "bn-IN": "পরবর্তী সুপারিশ",
    },
    "prog_recompute": {
        "en-IN": "Recompute recommendation",
        "hi-IN": "सुझाव फिर से निकालें",
        "te-IN": "సిఫార్సును మళ్లీ లెక్కించండి",
        "ta-IN": "பரிந்துரையை மீண்டும் கணக்கிடு",
        "bn-IN": "সুপারিশ পুনরায় হিসাব করা",
    },
    "prog_per_lesson": {
        "en-IN": "Per lesson",
        "hi-IN": "प्रत्येक पाठ",
        "te-IN": "ఒక్కో పాఠానికి",
        "ta-IN": "ஒரு பாடத்திற்கு",
        "bn-IN": "প্রতি পাঠে",
    },
    "prog_log": {
        "en-IN": "What the log says",
        "hi-IN": "लॉग क्या कहता है",
        "te-IN": "లాగ్ ఏం చెబుతోంది",
        "ta-IN": "பதிவு என்ன சொல்கிறது",
        "bn-IN": "লগে কী আছে",
    },
    "ana_per_day": {
        "en-IN": "Events per day",
        "hi-IN": "प्रति दिन घटनाएँ",
        "te-IN": "రోజుకు ఎన్ని ఈవెంట్\u200cలు",
        "ta-IN": "ஒரு நாளைக்கு நிகழ்வுகள்",
        "bn-IN": "প্রতিদিন ইভেন্ট",
    },
    "ana_by_lang": {
        "en-IN": "Events by language",
        "hi-IN": "भाषा के अनुसार घटनाएँ",
        "te-IN": "భాషను బట్టి ఈవెంట్\u200cలు",
        "ta-IN": "மொழியின் அடிப்படையில் நிகழ்வுகள்",
        "bn-IN": "ভাষানুযায়ী ইভেন্ট",
    },
    "ana_top": {
        "en-IN": "What fires most",
        "hi-IN": "सबसे अधिक क्या होता है",
        "te-IN": "ఎక్కువగా జరిగేవి",
        "ta-IN": "எது அதிகம் நடக்கிறது",
        "bn-IN": "সবচেয়ে বেশি কী ঘটে",
    },
    "ana_struggle": {
        "en-IN": "Struggle list",
        "hi-IN": "कठिनाई सूची",
        "te-IN": "కష్టపడుతున్న అంశాల జాబితా",
        "ta-IN": "சிரமப்படும் பட்டியல்",
        "bn-IN": "সংগ্রামের তালিকা",
    },
    "ana_refresh": {
        "en-IN": "Refresh export",
        "hi-IN": "एक्सपोर्ट रीफ़्रेश करें",
        "te-IN": "ఎక్స్\u200cపోర్ట్\u200cను రీఫ్రెష్ చేయండి",
        "ta-IN": "ஏற்றுமதியை புதுப்பிக்க",
        "bn-IN": "রপ্তানি রিফ্রেশ করা",
    },
    "ana_tutor_turns": {
        "en-IN": "Tutor turns",
        "hi-IN": "शिक्षक के उत्तर",
        "te-IN": "ట్యూటర్ మారడం",
        "ta-IN": "ஆசிரியரின் பதில்கள்",
        "bn-IN": "শিক্ষকের পালা",
    },
    "ana_refusals": {
        "en-IN": "Honest refusals",
        "hi-IN": "ईमानदार इनकार",
        "te-IN": "నిజాయితీగా తిరస్కరించడం",
        "ta-IN": "நேர்மையான மறுப்புகள்",
        "bn-IN": "সততার সাথে প্রত্যাখ্যান",
    },
    "ana_quizzes": {
        "en-IN": "Quizzes taken",
        "hi-IN": "दी गई प्रश्नोत्तरी",
        "te-IN": "తీసుకున్న క్విజ్\u200cలు",
        "ta-IN": "எடுத்த வினாடி வினாக்கள்",
        "bn-IN": "দেওয়া কুইজ",
    },
    "ana_translations": {
        "en-IN": "Translations",
        "hi-IN": "अनुवाद",
        "te-IN": "అనువాదాలు",
        "ta-IN": "மொழிபெயர்ப்புகள்",
        "bn-IN": "অনুবাদ",
    },
    "ana_cache": {
        "en-IN": "Cache hit rate",
        "hi-IN": "कैश हिट दर",
        "te-IN": "క్యాష్ హిట్ రేట్",
        "ta-IN": "கேச் ஹிட் வீதம்",
        "bn-IN": "ক্যাশ হিট রেট",
    },
    "ana_latency": {
        "en-IN": "Average latency",
        "hi-IN": "औसत विलंब",
        "te-IN": "సగటు లేటెన్సీ",
        "ta-IN": "சராசரி தாமதம்",
        "bn-IN": "গড় ল্যাটেন্সি",
    },
    "font_size": {
        "en-IN": "Font size",
        "hi-IN": "अक्षर आकार",
        "te-IN": "ఫాంట్ సైజు",
        "ta-IN": "எழுத்துரு அளவு",
        "bn-IN": "ফন্টের সাইজ",
    },
    "nav_tutor": {
        "en-IN": "Tutor",
        "hi-IN": "शिक्षक",
        "bn-IN": "শিক্ষক",
        "ta-IN": "ஆசிரியர்",
        "te-IN": "ట్యూటర్",
    },
    "nav_progress": {
        "en-IN": "Progress",
        "hi-IN": "प्रगति",
        "bn-IN": "অগ্রগতি",
        "ta-IN": "முன்னேற்றம்",
        "te-IN": "ప్రోగ్రెస్",
    },
    "nav_learn": {
        "en-IN": "Learn",
        "hi-IN": "सीखें",
        "bn-IN": "শেখুন",
        "ta-IN": "கற்றுக்கொள்ள",
        "te-IN": "నేర్చుకోండి",
    },
    "learn_read_in": {
        "en-IN": "Read in",
        "hi-IN": "इस भाषा में पढ़ें",
        "bn-IN": "এই ভাষায় পড়ুন",
        "ta-IN": "இந்த மொழியில் படிக்க",
        "te-IN": "ఈ భాషలో చదవండి",
    },
    "learn_quiz": {
        "en-IN": "Quiz",
        "hi-IN": "प्रश्नोत्तरी",
        "bn-IN": "কুইজ",
        "ta-IN": "வினாடி வினா",
        "te-IN": "క్విజ్",
    },
    "learn_check": {
        "en-IN": "Check answers",
        "hi-IN": "उत्तर जाँचें",
        "bn-IN": "উত্তরগুলো দেখুন",
        "ta-IN": "விடைகளைச் சரிபார்க்க",
        "te-IN": "సమాధానాలు చూడండి",
    },
    "learn_score": {
        "en-IN": "Your score",
        "hi-IN": "आपका स्कोर",
        "bn-IN": "আপনার স্কোর",
        "ta-IN": "உங்கள் மதிப்பெண்",
        "te-IN": "మీ స్కోరు",
    },
    "learn_tap": {
        "en-IN": "Tap a term to see its meaning",
        "hi-IN": "अर्थ देखने के लिए किसी शब्द पर टैप करें",
        "bn-IN": "কোনো শব্দের অর্থ দেখতে সেটিতে ট্যাপ করুন",
        "ta-IN": "ஒரு சொல்லின் பொருளைப் பார்க்க அதைத் தட்டவும்",
        "te-IN": "పదం అర్థం చూడటానికి దానిపై నొక్కండి",
    },
    "learn_glossary": {
        "en-IN": "Glossary",
        "hi-IN": "शब्दावली",
        "bn-IN": "শব্দকোষ",
        "ta-IN": "சொற்பொருள்",
        "te-IN": "పదకోశం",
    },
    "learn_lessons": {
        "en-IN": "Lessons",
        "hi-IN": "पाठ",
        "bn-IN": "পাঠ",
        "ta-IN": "பாடங்கள்",
        "te-IN": "పాఠాలు",
    },
    "tr_title": {
        "en-IN": "Translate anything",
        "hi-IN": "कुछ भी अनुवाद करें",
        "bn-IN": "কিছু অনুবাদ করুন",
        "ta-IN": "எதையாவது மொழிபெயர்க்கவும்",
        "te-IN": "ఏదైనా అనువదించు",
    },
    "tr_source_label": {
        "en-IN": "Type or paste text",
        "hi-IN": "टेक्स्ट लिखें या चिपकाएँ",
        "bn-IN": "টেক্সট টাইপ বা পেস্ট করুন",
        "ta-IN": "உரை எழுதவும் அல்லது ஒட்டவும்",
        "te-IN": "టెక్స్ట్ టైప్ చేయండి లేదా పేస్ట్ చేయండి",
    },
    "tr_button": {
        "en-IN": "Translate",
        "hi-IN": "अनुवाद करें",
        "bn-IN": "অনুবাদ করুন",
        "ta-IN": "மொழிபெயர்க்கவும்",
        "te-IN": "అనువదించు",
    },
    "tr_result": {
        "en-IN": "Result",
        "hi-IN": "परिणाम",
        "bn-IN": "ফলাফল",
        "ta-IN": "முடிவு",
        "te-IN": "ఫలితం",
    },
    "tr_copy": {
        "en-IN": "Copy",
        "hi-IN": "कॉपी करें",
        "bn-IN": "কপি",
        "ta-IN": "நகலெடுக்கவும்",
        "te-IN": "కాపీ",
    },
    "tr_cached": {
        "en-IN": "Served from cache",
        "hi-IN": "कैश से दिया गया",
        "bn-IN": "ক্যাশ থেকে পরিবেশন করা হয়েছে",
        "ta-IN": "கேச்சிலிருந்து வழங்கப்பட்டது",
        "te-IN": "క్యాష్ నుండి అందించబడింది",
    },
    "tr_recent": {
        "en-IN": "Recent translations",
        "hi-IN": "हाल के अनुवाद",
        "bn-IN": "সাম্প্রতিক অনুবাদ",
        "ta-IN": "சமீபத்திய மொழிபெயர்ப்புகள்",
        "te-IN": "ఇటీవలి అనువాదాలు",
    },
    "tr_example": {
        "en-IN": "Try an example",
        "hi-IN": "एक उदाहरण आज़माएँ",
        "bn-IN": "একটি উদাহরণ চেষ্টা করুন",
        "ta-IN": "ஒரு உதாரணத்தை முயற்சிக்கவும்",
        "te-IN": "ఒక ఉదాహరణ ప్రయత్నించండి",
    },
}


def t(key: str, lang: str | None = None) -> str:
    """Translate a UI key into ``lang``, falling back to English, then the key."""
    entry = UI_STRINGS.get(key)
    if entry is None:
        return key
    code = lang or config.DEFAULT_LANG
    return entry.get(code) or entry.get(config.DEFAULT_LANG) or key


def coverage() -> dict[str, int]:
    """How many keys each language has — surfaced as a Phase 5 QA check."""
    return {
        code: sum(1 for entry in UI_STRINGS.values() if code in entry)
        for code in config.LANG_CODES
    }

import re

# Localized keyword lexicons
BOTANICAL_TERMS = {
    "plant", "herb", "root", "leaf", "leaves", "stem", "flower", "seed", "bark", "extract",
    "taxonomy", "species", "genus", "family", "shrub", "tree", "botanical", "rhizome", "aerial"
}

PHARMA_TERMS = {
    "healing", "symptom", "mechanism", "treatment", "medicine", "efficacy", "clinical",
    "trial", "dosage", "compound", "phytochemical", "alkaloid", "flavonoid", "anti-inflammatory",
    "antioxidant", "therapeutic", "pharmacological", "pharmacology", "bioactive", "receptor",
    "inhibitor", "metabolism", "toxicity"
}

HISTORY_TERMS = {
    "ancient", "mythology", "cultural", "traditional", "provenance", "ayurveda", "tcm",
    "chinese medicine", "folk", "historical", "indigenous", "shamanic", "ritual", "tribe",
    "ethnobotany", "ethnobotanical", "heritage", "antiquity", "lore",
    "egyptian medicine", "greek medicine", "mesopotamian medicine", "persian medicine",
    "mesoamerican medicine", "arabic medicine", "islamic medicine", "yoruba traditional medicine",
    "yoruba medicine", "norse healing"
,
    "charaka samhita", "sushruta samhita", "ashtanga hridaya", "ashtanga sangraha", "bhela samhita", "kashyapa samhita", "bhavaprakasha", "madhava nidana", "sharangadhara samhita", "rasaratna samuccaya", "huangdi neijing", "shennong bencao jing", "shanghan lun", "jingui yaolue", "bencao gangmu", "zhenjiu jiayi jing", "ebers papyrus", "edwin smith papyrus", "kahun gynecological papyrus", "hearst papyrus", "london medical papyrus", "berlin papyrus", "hippocratic corpus", "on the nature of man", "on fractures", "on joints", "de materia medica", "on the usefulness of the parts", "diagnostic handbook", "assur medical tablets", "nineveh medical tablets", "babylonian therapeutic texts", "uruanna", "cuneiform healing tablets", "the canon of medicine", "al-hawi", "zakhireye khwarazmshahi", "kitab al-mansuri", "badianus manuscript", "florentine codex", "libellus de medicinalibus indorum herbis", "maya medicinal codices", "al-tasrif", "kitab al-maliki", "kitab al-saydalah", "ifá medicinal verses", "yoruba herbal corpus", "colonial ethnobotanical records", "lacnunga", "bald's leechbook", "poetic edda", "prose edda", "icelandic healing manuscripts"}


BOOK_MYTHOLOGY_MAP = {
    "Charaka Samhita": "Ayurveda",
    "Sushruta Samhita": "Ayurveda",
    "Ashtanga Hridaya": "Ayurveda",
    "Ashtanga Sangraha": "Ayurveda",
    "Bhela Samhita": "Ayurveda",
    "Kashyapa Samhita": "Ayurveda",
    "Bhavaprakasha": "Ayurveda",
    "Madhava Nidana": "Ayurveda",
    "Sharangadhara Samhita": "Ayurveda",
    "Rasaratna Samuccaya": "Ayurveda",
    "Huangdi Neijing": "TCM",
    "Shennong Bencao Jing": "TCM",
    "Shanghan Lun": "TCM",
    "Jingui Yaolue": "TCM",
    "Bencao Gangmu": "TCM",
    "Zhenjiu Jiayi Jing": "TCM",
    "Ebers Papyrus": "Ancient Egyptian medicine",
    "Edwin Smith Papyrus": "Ancient Egyptian medicine",
    "Kahun Gynecological Papyrus": "Ancient Egyptian medicine",
    "Hearst Papyrus": "Ancient Egyptian medicine",
    "London Medical Papyrus": "Ancient Egyptian medicine",
    "Berlin Papyrus": "Ancient Egyptian medicine",
    "Hippocratic Corpus": "Ancient Greek medicine",
    "On the Nature of Man": "Ancient Greek medicine",
    "On Fractures": "Ancient Greek medicine",
    "On Joints": "Ancient Greek medicine",
    "De Materia Medica": "Ancient Greek medicine",
    "On the Usefulness of the Parts": "Ancient Greek medicine",
    "Diagnostic Handbook": "Mesopotamian medicine",
    "Assur Medical Tablets": "Mesopotamian medicine",
    "Nineveh Medical Tablets": "Mesopotamian medicine",
    "Babylonian Therapeutic Texts": "Mesopotamian medicine",
    "Uruanna": "Mesopotamian medicine",
    "Cuneiform Healing Tablets": "Mesopotamian medicine",
    "The Canon of Medicine": "Persian medicine",
    "Al-Hawi": "Persian medicine",
    "Zakhireye Khwarazmshahi": "Persian medicine",
    "Kitab al-Mansuri": "Persian medicine",
    "Badianus Manuscript": "Mesoamerican medicine",
    "Florentine Codex": "Mesoamerican medicine",
    "Libellus de Medicinalibus Indorum Herbis": "Mesoamerican medicine",
    "Maya Medicinal Codices": "Mesoamerican medicine",
    "Al-Tasrif": "Arabic and Islamic medicine",
    "Kitab al-Maliki": "Arabic and Islamic medicine",
    "Kitab al-Saydalah": "Arabic and Islamic medicine",
    "Ifá Medicinal Verses": "Yoruba traditional medicine",
    "Yoruba Herbal Corpus": "Yoruba traditional medicine",
    "Colonial Ethnobotanical Records": "Yoruba traditional medicine",
    "Lacnunga": "Norse healing traditions",
    "Bald's Leechbook": "Norse healing traditions",
    "Poetic Edda": "Norse healing traditions",
    "Prose Edda": "Norse healing traditions",
    "Icelandic Healing Manuscripts": "Norse healing traditions"
}

NOISE_TERMS = {
    "buy now", "add to cart", "cookie policy", "privacy policy", "terms of service",
    "shopping cart", "checkout", "subscribe", "newsletter", "copyright", "all rights reserved",
    "click here", "read more", "advertisement", "sponsored", "sale", "discount", "promo code",
    "login", "sign up", "password", "accept cookies"
}

def chunk_text_sliding_window(text: str, window_size: int = 150, overlap: int = 50) -> list[str]:
    """
    Splits text into overlapping windows of words/tokens.
    """
    if not text:
        return []

    words = text.split()
    chunks = []

    if len(words) <= window_size:
        return [" ".join(words)]

    step = window_size - overlap
    if step <= 0:
        step = window_size # Fallback if overlap is incorrectly set too high

    for i in range(0, len(words), step):
        chunk_words = words[i:i + window_size]
        chunks.append(" ".join(chunk_words))
        if i + window_size >= len(words):
            break

    return chunks

def count_term_occurrences(text: str, terms: set) -> int:
    """
    Counts how many of the given terms appear in the text as whole words or phrases.
    """
    count = 0
    for term in terms:
        if re.search(rf'\b{re.escape(term)}\b', text):
            count += 1
    return count

def calculate_chunk_score(chunk: str, target_herb: str = "") -> float:
    """
    Calculates a Confidence Score for a chunk using a density approach.
    """
    chunk_lower = chunk.lower()

    # Simple word tokenization for density calculation
    words = re.findall(r'\b\w+\b', chunk_lower)
    if not words:
        return 0.0

    word_count = len(words)

    # Count occurrences of lexicon terms
    botanical_count = count_term_occurrences(chunk_lower, BOTANICAL_TERMS)
    pharma_count = count_term_occurrences(chunk_lower, PHARMA_TERMS)
    history_count = count_term_occurrences(chunk_lower, HISTORY_TERMS)
    noise_count = count_term_occurrences(chunk_lower, NOISE_TERMS)

    # Target awareness
    target_count = 0
    if target_herb:
        target_count = len(re.findall(rf'\b{re.escape(target_herb.lower())}\b', chunk_lower))

    # Weighting the scores
    # We want chunks that are dense in relevant terms.
    positive_score = (botanical_count * 1.5) + (pharma_count * 2.0) + (history_count * 1.5)

    # Positive multiplier for target occurrences
    positive_score += (target_count * 5.0)

    # Density factor: if chunk is long but has few keywords, it's diluted.
    # Normalizing by words per 100
    density_factor = max(1.0, word_count / 100.0)

    base_score = positive_score / density_factor

    # Fractional dampener for noise instead of flat subtraction
    if noise_count > 0:
        dampener = 1.0 - min(0.9, noise_count * 0.1) # Max 90% reduction
        base_score *= dampener

    final_score = base_score

    return final_score

def evaluate_chunks(chunks: list[str], target_herb: str = "") -> list[dict]:
    """
    Applies scoring to all chunks and returns structured evaluations.
    """
    evaluated = []
    for chunk in chunks:
        score = calculate_chunk_score(chunk, target_herb)
        evaluated.append({
            "text": chunk,
            "score": score
        })
    return evaluated

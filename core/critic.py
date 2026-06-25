import re

# Pre-compile the regex patterns using re.compile at the module level
BOTANICAL_PATTERNS = [re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE) for term in [
    "plant", "herb", "root", "leaf", "leaves", "stem", "flower", "seed", "bark", "extract",
    "taxonomy", "species", "genus", "family", "shrub", "tree", "botanical", "rhizome", "aerial"
]]

PHARMA_PATTERNS = [re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE) for term in [
    "healing", "symptom", "mechanism", "treatment", "medicine", "efficacy", "clinical",
    "trial", "dosage", "compound", "phytochemical", "alkaloid", "flavonoid", "anti-inflammatory",
    "antioxidant", "therapeutic", "pharmacological", "pharmacology", "bioactive", "receptor",
    "inhibitor", "metabolism", "toxicity"
]]

HISTORY_PATTERNS = [re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE) for term in [
    "ancient", "mythology", "cultural", "traditional", "provenance", "ayurveda", "tcm",
    "chinese medicine", "folk", "historical", "indigenous", "shamanic", "ritual", "tribe",
    "ethnobotany", "ethnobotanical", "heritage", "antiquity", "lore"
]]

NOISE_PATTERNS = [re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE) for term in [
    "buy now", "add to cart", "cookie policy", "privacy policy", "terms of service",
    "shopping cart", "checkout", "subscribe", "newsletter", "copyright", "all rights reserved",
    "click here", "read more", "advertisement", "sponsored", "sale", "discount", "promo code",
    "login", "sign up", "password", "accept cookies"
]]

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

def count_term_occurrences(text: str, compiled_patterns: list) -> int:
    """
    Counts how many of the given pre-compiled terms appear in the text.
    """
    count = 0
    for pattern in compiled_patterns:
        if pattern.search(text):
            count += 1
    return count

def calculate_chunk_score(chunk: str, herb_name: str) -> float:
    """
    Calculates a Confidence Score for a chunk using a density approach.
    """
    chunk_lower = chunk.lower()

    # Simple word tokenization for density calculation
    words = re.findall(r'\b\w+\b', chunk_lower)
    if not words:
        return 0.0

    word_count = len(words)

    # Count occurrences of lexicon terms using pre-compiled patterns
    botanical_count = count_term_occurrences(chunk_lower, BOTANICAL_PATTERNS)
    pharma_count = count_term_occurrences(chunk_lower, PHARMA_PATTERNS)
    history_count = count_term_occurrences(chunk_lower, HISTORY_PATTERNS)
    noise_count = count_term_occurrences(chunk_lower, NOISE_PATTERNS)

    # Target Awareness: count occurrences of the specific herb_name
    herb_occurrences = 0
    if herb_name:
        herb_pattern = re.compile(rf'\b{re.escape(herb_name.lower())}\b')
        herb_occurrences = len(herb_pattern.findall(chunk_lower))

    # Weighting the scores
    # We want chunks that are dense in relevant terms.
    positive_score = (botanical_count * 1.5) + (pharma_count * 2.0) + (history_count * 1.5) + (herb_occurrences * 5.0)

    # Density factor: if chunk is long but has few keywords, it's diluted.
    # Normalizing by words per 100
    density_factor = max(1.0, word_count / 100.0)

    base_score = positive_score / density_factor

    # Soften the noise trap: use a fractional dampener instead of flat subtraction
    final_score = base_score * (0.9 ** noise_count)

    return final_score

def evaluate_chunks(chunks: list[str], herb_name: str) -> list[dict]:
    """
    Applies scoring to all chunks and returns structured evaluations.
    """
    evaluated = []
    for chunk in chunks:
        score = calculate_chunk_score(chunk, herb_name)
        evaluated.append({
            "text": chunk,
            "score": score
        })
    return evaluated

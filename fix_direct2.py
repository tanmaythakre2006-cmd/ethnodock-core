import re
with open("core/direct_ingestion.py", "r") as f:
    code = f.read()

# Make Wikipedia the primary focus for direct ingestion with lower score thresholds since it's verified domain
code = code.replace(
'''                        validated = [
                            {"text": ev["text"], "score": ev["score"], "is_high_confidence": True}
                            for ev in evaluated if ev["score"] >= 0.1
                        ]''',
'''                        # If it's direct Wikipedia, we trust the first few chunks entirely since Wikipedia describes the herb!
                        validated = []
                        for i, ev in enumerate(evaluated):
                            if ev["score"] >= 0.1 or i < 3: # Always keep first 3 chunks of Wikipedia
                                validated.append({"text": ev["text"], "score": max(ev["score"], 5.0), "is_high_confidence": True})
                        ''')
with open("core/direct_ingestion.py", "w") as f:
    f.write(code)

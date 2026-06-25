import json
from core.pruner import merge_matrices, prune_empty_nodes

def test_pruner():
    matrix1 = {
        "mythologies": {
            "Ayurveda": {
                "Atharva Veda": {
                    "nomenclature": ["Ashwagandha"],
                    "species": ["Withania somnifera"],
                    "properties": ["Adaptogen"]
                },
                "Charaka Samhita": {
                    "nomenclature": [],
                    "species": [],
                    "properties": [] # Empty properties
                }
            },
            "Empty_Mythology": {}
        }
    }

    matrix2 = {
        "mythologies": {
            "Ayurveda": {
                "Atharva Veda": {
                    "nomenclature": ["Indian Ginseng"],
                    "species": [],
                    "properties": ["Stress relief", "Vitality"]
                }
            },
            "TCM": {
                "Shennong Bencao Jing": {
                    "nomenclature": [],
                    "species": [],
                    "properties": []
                }
            }
        }
    }

    matrix3 = {
        "mythologies": {
            "Ayurveda": {
                "Atharva Veda": {
                    "nomenclature": "Winter Cherry", # String instead of list
                    "species": "W. somnifera",
                    "properties": "Sleep aid"
                }
            }
        }
    }

    print("Testing merge_matrices...")
    merged = merge_matrices([matrix1, matrix2, matrix3])
    print(json.dumps(merged, indent=2))

    assert "Ayurveda" in merged["mythologies"]
    assert "Atharva Veda" in merged["mythologies"]["Ayurveda"]
    assert "Ashwagandha" in merged["mythologies"]["Ayurveda"]["Atharva Veda"]["nomenclature"]
    assert "Indian Ginseng" in merged["mythologies"]["Ayurveda"]["Atharva Veda"]["nomenclature"]
    assert "Winter Cherry" in merged["mythologies"]["Ayurveda"]["Atharva Veda"]["nomenclature"]
    assert "Stress relief" in merged["mythologies"]["Ayurveda"]["Atharva Veda"]["properties"]
    assert "Sleep aid" in merged["mythologies"]["Ayurveda"]["Atharva Veda"]["properties"]

    print("\nTesting prune_empty_nodes...")
    pruned = prune_empty_nodes(merged)
    print(json.dumps(pruned, indent=2))

    assert "Charaka Samhita" not in pruned["mythologies"].get("Ayurveda", {})
    assert "Empty_Mythology" not in pruned["mythologies"]
    assert "TCM" not in pruned["mythologies"]
    assert "Ayurveda" in pruned["mythologies"]

    print("\nPruner tests passed.")

if __name__ == "__main__":
    test_pruner()

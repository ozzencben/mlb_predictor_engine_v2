import requests

def test_hand(person_id):
    url = f"https://statsapi.mlb.com/api/v1/people/{person_id}"
    res = requests.get(url).json()
    people = res.get("people", [])
    if people:
        person = people[0]
        print("Keys:", person.keys())
        print("pitchHand:", person.get("pitchHand"))
        print("fullName:", person.get("fullName"))

if __name__ == "__main__":
    test_hand(673540) # Sasaki

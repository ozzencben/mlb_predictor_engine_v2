import asyncio
import json
import os
import httpx
from datetime import datetime
from app.services.prediction_runner import PredictionRunner

async def test_lineups_caching():
    print("[TEST] Starting Lineups Caching and Fallback Logic Tests...")
    
    # 1. Instantiate the PredictionRunner
    runner = PredictionRunner()
    
    # Ensure a clean slate for the test by clearing cache entries for a test gamePk
    test_game_pk = 999999
    test_game_pk_str = str(test_game_pk)
    if test_game_pk_str in runner.lineups_cache:
        del runner.lineups_cache[test_game_pk_str]
        runner._save_json(runner.lineups_cache_path, runner.lineups_cache)
        print("[CLEAN] Cleared existing test cache entry.")

    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json_data = json_data
        def json(self):
            return self._json_data

    class MockAsyncClient:
        def __init__(self):
            self.boxscore_calls = 0
            self.schedule_calls = 0
            self.boxscore_data = {
                "teams": {
                    "away": {
                        "battingOrder": [], # Empty, meaning unofficial
                        "players": {}
                    },
                    "home": {
                        "battingOrder": [],
                        "players": {}
                    }
                }
            }
            # Last completed game boxscore (fallback)
            self.fallback_boxscore_data = {
                "teams": {
                    "away": {
                        "battingOrder": [101, 102, 103, 104, 105, 106, 107, 108, 109],
                        "players": {
                            "ID101": {"person": {"fullName": "Away Fallback 1"}, "position": {"abbreviation": "CF"}},
                            "ID102": {"person": {"fullName": "Away Fallback 2"}, "position": {"abbreviation": "2B"}},
                            "ID103": {"person": {"fullName": "Away Fallback 3"}, "position": {"abbreviation": "RF"}},
                            "ID104": {"person": {"fullName": "Away Fallback 4"}, "position": {"abbreviation": "1B"}},
                            "ID105": {"person": {"fullName": "Away Fallback 5"}, "position": {"abbreviation": "DH"}},
                            "ID106": {"person": {"fullName": "Away Fallback 6"}, "position": {"abbreviation": "3B"}},
                            "ID107": {"person": {"fullName": "Away Fallback 7"}, "position": {"abbreviation": "LF"}},
                            "ID108": {"person": {"fullName": "Away Fallback 8"}, "position": {"abbreviation": "SS"}},
                            "ID109": {"person": {"fullName": "Away Fallback 9"}, "position": {"abbreviation": "C"}}
                        }
                    },
                    "home": {
                        "battingOrder": [201, 202, 203, 204, 205, 206, 207, 208, 209],
                        "players": {
                            "ID201": {"person": {"fullName": "Home Fallback 1"}, "position": {"abbreviation": "LF"}},
                            "ID202": {"person": {"fullName": "Home Fallback 2"}, "position": {"abbreviation": "SS"}},
                            "ID203": {"person": {"fullName": "Home Fallback 3"}, "position": {"abbreviation": "DH"}},
                            "ID204": {"person": {"fullName": "Home Fallback 4"}, "position": {"abbreviation": "1B"}},
                            "ID205": {"person": {"fullName": "Home Fallback 5"}, "position": {"abbreviation": "3B"}},
                            "ID206": {"person": {"fullName": "Home Fallback 6"}, "position": {"abbreviation": "RF"}},
                            "ID207": {"person": {"fullName": "Home Fallback 7"}, "position": {"abbreviation": "CF"}},
                            "ID208": {"person": {"fullName": "Home Fallback 8"}, "position": {"abbreviation": "2B"}},
                            "ID209": {"person": {"fullName": "Home Fallback 9"}, "position": {"abbreviation": "C"}}
                        }
                    }
                }
            }

        async def get(self, url, timeout=10.0):
            if "boxscore" in url:
                self.boxscore_calls += 1
                if "999999" in url:
                    # Return today's game boxscore status
                    return MockResponse(200, self.boxscore_data)
                else:
                    # Return fallback game boxscore status
                    return MockResponse(200, self.fallback_boxscore_data)
            elif "schedule" in url:
                self.schedule_calls += 1
                # Return schedule of past games containing completed gamePk
                schedule_data = {
                    "dates": [
                        {
                            "games": [
                                {
                                    "gamePk": 888888,
                                    "status": {"statusCode": "F"} # Completed
                                }
                            ]
                        }
                    ]
                }
                return MockResponse(200, schedule_data)
            return MockResponse(404, {})

    client = MockAsyncClient()

    # --- TEST STEP 1: Unofficial lineups should trigger fallback and cache as is_official=False ---
    print("\n--- TEST STEP 1: Fetching unofficial lineup (First execution) ---")
    away, home = await runner.get_lineup_for_game(client, test_game_pk, 147, 112)
    
    assert client.boxscore_calls == 3, f"Expected 3 boxscore calls (1 for current game, 2 for fallbacks), got {client.boxscore_calls}"
    assert client.schedule_calls == 2, f"Expected 2 schedule calls (1 for away last completed, 1 for home last completed), got {client.schedule_calls}"
    assert len(away) == 9, "Expected 9 batters"
    assert away[0]["name"] == "Away Fallback 1", f"Expected 'Away Fallback 1', got {away[0]['name']}"
    
    # Verify saved cache
    cached_entry = runner.lineups_cache[test_game_pk_str]
    assert cached_entry["is_official"] is False, "Cache should show is_official as False"
    print("[SUCCESS] Step 1 passed: Fallback generated and saved in cache as is_official=False.")

    # Reset client counters
    client.boxscore_calls = 0
    client.schedule_calls = 0

    # --- TEST STEP 2: Running again when still unofficial should hit cache without new schedule scrape ---
    print("\n--- TEST STEP 2: Fetching again when still unofficial (Cache lookup + boxscore reload retry) ---")
    away2, home2 = await runner.get_lineup_for_game(client, test_game_pk, 147, 112)
    
    assert client.boxscore_calls == 1, f"Expected exactly 1 boxscore call to check live status, got {client.boxscore_calls}"
    assert client.schedule_calls == 0, f"Expected 0 schedule calls (reusing cached fallback), got {client.schedule_calls}"
    assert len(away2) == 9
    assert away2[0]["name"] == "Away Fallback 1"
    print("[SUCCESS] Step 2 passed: Only 1 API call made to double-check live boxscore; skipped redundant fallback schedule fetches.")

    # Reset client counters
    client.boxscore_calls = 0
    client.schedule_calls = 0

    # --- TEST STEP 3: Official starting lineups released: boxscore call should succeed and cache as is_official=True ---
    print("\n--- TEST STEP 3: Official lineups become available ---")
    client.boxscore_data = {
        "teams": {
            "away": {
                "battingOrder": [301, 302, 303, 304, 305, 306, 307, 308, 309],
                "players": {
                    "ID301": {"person": {"fullName": "Aaron Judge"}, "position": {"abbreviation": "CF"}},
                    "ID302": {"person": {"fullName": "Juan Soto"}, "position": {"abbreviation": "RF"}},
                    "ID303": {"person": {"fullName": "Giancarlo Stanton"}, "position": {"abbreviation": "DH"}},
                    "ID304": {"person": {"fullName": "Anthony Rizzo"}, "position": {"abbreviation": "1B"}},
                    "ID305": {"person": {"fullName": "Gleyber Torres"}, "position": {"abbreviation": "2B"}},
                    "ID306": {"person": {"fullName": "Alex Verdugo"}, "position": {"abbreviation": "LF"}},
                    "ID307": {"person": {"fullName": "Anthony Volpe"}, "position": {"abbreviation": "SS"}},
                    "ID308": {"person": {"fullName": "Austin Wells"}, "position": {"abbreviation": "C"}},
                    "ID309": {"person": {"fullName": "Oswaldo Cabrera"}, "position": {"abbreviation": "3B"}}
                }
            },
            "home": {
                "battingOrder": [401, 402, 403, 404, 405, 406, 407, 408, 409],
                "players": {
                    "ID401": {"person": {"fullName": "Shohei Ohtani"}, "position": {"abbreviation": "DH"}},
                    "ID402": {"person": {"fullName": "Mookie Betts"}, "position": {"abbreviation": "SS"}},
                    "ID403": {"person": {"fullName": "Freddie Freeman"}, "position": {"abbreviation": "1B"}},
                    "ID404": {"person": {"fullName": "Will Smith"}, "position": {"abbreviation": "C"}},
                    "ID405": {"person": {"fullName": "Max Muncy"}, "position": {"abbreviation": "3B"}},
                    "ID406": {"person": {"fullName": "Teoscar Hernandez"}, "position": {"abbreviation": "LF"}},
                    "ID407": {"person": {"fullName": "James Outman"}, "position": {"abbreviation": "CF"}},
                    "ID408": {"person": {"fullName": "Gavin Lux"}, "position": {"abbreviation": "2B"}},
                    "ID409": {"person": {"fullName": "Jason Heyward"}, "position": {"abbreviation": "RF"}}
                }
            }
        }
    }

    away3, home3 = await runner.get_lineup_for_game(client, test_game_pk, 147, 112)
    
    assert client.boxscore_calls == 1, f"Expected 1 boxscore call to check status, got {client.boxscore_calls}"
    assert client.schedule_calls == 0, "Expected 0 schedule calls"
    assert len(away3) == 9
    assert away3[0]["name"] == "Aaron Judge", f"Expected 'Aaron Judge', got {away3[0]['name']}"
    
    # Verify cache entry updated to is_official=True
    cached_entry3 = runner.lineups_cache[test_game_pk_str]
    assert cached_entry3["is_official"] is True, "Cache should now show is_official as True"
    print("[SUCCESS] Step 3 passed: Official lineups successfully detected, cache updated and marked is_official=True.")

    # Reset client counters
    client.boxscore_calls = 0
    client.schedule_calls = 0

    # --- TEST STEP 4: Subsequent execution should read official data from cache without ANY API calls ---
    print("\n--- TEST STEP 4: Fetching official lineup again (Cache lookup only) ---")
    away4, home4 = await runner.get_lineup_for_game(client, test_game_pk, 147, 112)
    
    assert client.boxscore_calls == 0, f"Expected 0 boxscore calls (read from cache), got {client.boxscore_calls}"
    assert client.schedule_calls == 0, "Expected 0 schedule calls"
    assert len(away4) == 9
    assert away4[0]["name"] == "Aaron Judge"
    print("[SUCCESS] Step 4 passed: Read directly from cache with 0 API overhead since is_official is True.")

    # 5. Clean up test cache entry
    del runner.lineups_cache[test_game_pk_str]
    runner._save_json(runner.lineups_cache_path, runner.lineups_cache)
    print("\n[CLEAN] Cleaned up test cache entry. All lineups tests completed successfully! Done.")

if __name__ == "__main__":
    asyncio.run(test_lineups_caching())

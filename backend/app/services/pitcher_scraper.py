import asyncio
import httpx
import json
import os
import requests
import tempfile
from datetime import datetime

from app.core.config import settings


class PitcherScraper:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(self.data_dir, exist_ok=True)

        self.current_year = datetime.now().year
        self.fip_constant = 3.15

        self.league_averages = {
            "era": 4.20,
            "fip": 4.20,
            "xera": 4.20,
            "xfip": 4.20,
            "k_bb_pct": 0.14,
            "throws": "R",
            "innings_pitched": 0.0,
            "wins": 0,
            "losses": 0,
            "record": "0-0",
        }

        # TCP/SSL Handshake maliyetini düşürmek için Session kullanımı
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.SCRAPER_USER_AGENT})

    def _atomic_save(self, filepath: str, data: dict):
        """Dosyanın bozulmasını önleyen atomik yazma işlemi."""
        dir_name = os.path.dirname(filepath)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, filepath)
        except Exception as e:
            os.remove(temp_path)
            raise e

    def _get_pitcher_id(self, pitcher_name: str) -> str:
        url = f"https://statsapi.mlb.com/api/v1/people/search?names={pitcher_name}"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("people"):
                return str(data["people"][0]["id"])
            return None
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Ağ Hatası (ID Arama - {pitcher_name}): {e}")
            return None
        except Exception:
            return None

    def _get_advanced_stats(self, person_id: str) -> dict:
        url = f"https://statsapi.mlb.com/api/v1/people/{person_id}?hydrate=stats(group=[pitching],type=[season],season={self.current_year})"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            people = data.get("people", [])
            if not people:
                return None

            throws = people[0].get("pitchHand", {}).get("code", "R")

            stats_list = people[0].get("stats", [])
            if not stats_list:
                return {"throws": throws}

            splits = stats_list[0].get("splits", [])
            if not splits:
                return {"throws": throws}

            stat_dict = splits[0].get("stat", {}).copy()
            stat_dict["throws"] = throws
            return stat_dict
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Ağ Hatası (Stat Çekme - {person_id}): {e}")
            return None
        except Exception:
            return None

    def build_pitcher_library(self):
        print(
            "🚀 Kırılmaz MLB Statcast Kütüphanesi Oluşturuluyor (W-L Kayıtları ile)..."
        )

        matchups_file = os.path.join(self.data_dir, "daily_matchups.json")
        try:
            with open(matchups_file, "r", encoding="utf-8") as f:
                matchups_data = json.load(f)
        except FileNotFoundError:
            print(
                "❌ daily_matchups.json bulunamadı. Lütfen önce matchup_scraper.py'yi çalıştırın."
            )
            return

        pitcher_names = set()
        for game in matchups_data.get("games", []):
            if game.get("away_pitcher") and game["away_pitcher"] != "TBD":
                pitcher_names.add(game["away_pitcher"])
            if game.get("home_pitcher") and game["home_pitcher"] != "TBD":
                pitcher_names.add(game["home_pitcher"])

        print(f"🔍 Toplam {len(pitcher_names)} adet başlangıç atıcısı (SP) aranıyor...")
        pitcher_library = {}

        for name in pitcher_names:
            print(f"⚾ Çekiliyor: {name}...", end=" ")

            p_id = self._get_pitcher_id(name)
            if not p_id:
                print("⚠️ ID Bulunamadı. Çaylak/Farklı İsim.")
                pitcher_library[name] = self.league_averages.copy()
                continue

            stats = self._get_advanced_stats(p_id)
            if not stats:
                print("⚠️ Bu sezon verisi yok. Lig ortalaması atandı.")
                pitcher_library[name] = self.league_averages.copy()
                continue

            throws = stats.get("throws", "R")
            era = float(stats.get("era", 4.20))
            ip = float(stats.get("inningsPitched", 0.1))
            hr = int(stats.get("homeRuns", 0))
            bb = int(stats.get("baseOnBalls", 0))
            k = int(stats.get("strikeOuts", 0))
            bf = int(stats.get("battersFaced", 1))
            wins = int(stats.get("wins", 0))
            losses = int(stats.get("losses", 0))

            # 1. Gerçek K-BB% Hesaplama
            if bf > 0:
                k_bb_pct = round((k / bf) - (bb / bf), 3)
                k_pct = k / bf
                bb_pct = bb / bf
            else:
                k_bb_pct = 0.0
                k_pct = 0.20
                bb_pct = 0.08

            # 2. FIP Hesaplama
            if ip > 0:
                fip = round(
                    max(
                        0.0, (((13 * hr) + (3 * bb) - (2 * k)) / ip) + self.fip_constant
                    ),
                    2,
                )
                expected_hr = (hr * 0.5) + ((ip * 1.15 / 9.0) * 0.5)
                xfip = round(
                    max(
                        0.0, (((13 * expected_hr) + (3 * bb) - (2 * k)) / ip) + self.fip_constant
                    ),
                    2,
                )
            else:
                fip = era
                xfip = era

            xera = round(max(1.5, min(7.5, 3.10 + 12.0 * bb_pct - 15.0 * k_pct)), 2)
            xera = round(xera * 0.7 + era * 0.3, 2)

            pitcher_library[name] = {
                "era": era,
                "fip": fip,
                "xera": xera,
                "xfip": xfip,
                "k_bb_pct": k_bb_pct,
                "throws": throws,
                "innings_pitched": ip,
                "wins": wins,
                "losses": losses,
                "record": f"{wins}-{losses}",
            }
            print(f"✅ Başarılı (W-L: {wins}-{losses} | FIP: {fip})")

        # Güvenli Kayıt (Atomik)
        output_path = os.path.join(self.data_dir, "pitcher_stats.json")
        history_dir = os.path.join(self.data_dir, "history")
        os.makedirs(history_dir, exist_ok=True)
        history_path = os.path.join(
            history_dir, f"{datetime.now().strftime('%Y-%m-%d')}_pitchers.json"
        )

        if pitcher_library:
            self._atomic_save(output_path, pitcher_library)
            self._atomic_save(history_path, pitcher_library)
            print(
                f"\n🎉 GÖREV TAMAM! {len(pitcher_library)} atıcının verileri güvenle kaydedildi."
            )
        else:
            print("\n⚠️ Uyarı: Hiçbir atıcı verisi bulunamadı, JSON güncellenmedi.")

    async def _get_pitcher_id_async(
        self, client: httpx.AsyncClient, pitcher_name: str
    ) -> str:
        url = f"https://statsapi.mlb.com/api/v1/people/search?names={pitcher_name}"
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            if data.get("people"):
                return str(data["people"][0]["id"])
            return None
        except Exception:
            return None

    async def _get_advanced_stats_async(
        self, client: httpx.AsyncClient, person_id: str
    ) -> dict:
        url = f"https://statsapi.mlb.com/api/v1/people/{person_id}?hydrate=stats(group=[pitching],type=[season],season={self.current_year})"
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            people = data.get("people", [])
            if not people:
                return None

            throws = people[0].get("pitchHand", {}).get("code", "R")

            stats_list = people[0].get("stats", [])
            if not stats_list:
                return {"throws": throws}

            splits = stats_list[0].get("splits", [])
            if not splits:
                return {"throws": throws}

            stat_dict = splits[0].get("stat", {}).copy()
            stat_dict["throws"] = throws
            return stat_dict
        except Exception:
            return None

    async def build_pitcher_library_async(self, client: httpx.AsyncClient):
        print(
            "🚀 Kırılmaz MLB Statcast Kütüphanesi Oluşturuluyor (W-L Kayıtları ile)..."
        )

        matchups_file = os.path.join(self.data_dir, "daily_matchups.json")
        try:
            with open(matchups_file, "r", encoding="utf-8") as f:
                matchups_data = json.load(f)
        except FileNotFoundError:
            print(
                "❌ daily_matchups.json bulunamadı. Lütfen önce matchup_scraper.py'yi çalıştırın."
            )
            return

        pitcher_names = set()
        for game in matchups_data.get("games", []):
            if game.get("away_pitcher") and game["away_pitcher"] != "TBD":
                pitcher_names.add(game["away_pitcher"])
            if game.get("home_pitcher") and game["home_pitcher"] != "TBD":
                pitcher_names.add(game["home_pitcher"])

        print(f"🔍 Toplam {len(pitcher_names)} adet başlangıç atıcısı (SP) aranıyor...")
        pitcher_library = {}

        for name in pitcher_names:
            print(f"⚾ Çekiliyor: {name}...", end=" ")

            p_id = await self._get_pitcher_id_async(client, name)
            if not p_id:
                print("⚠️ ID Bulunamadı. Çaylak/Farklı İsim.")
                pitcher_library[name] = self.league_averages.copy()
                continue

            stats = await self._get_advanced_stats_async(client, p_id)
            if not stats:
                print("⚠️ Bu sezon verisi yok. Lig ortalaması atandı.")
                pitcher_library[name] = self.league_averages.copy()
                continue

            throws = stats.get("throws", "R")
            era = float(stats.get("era", 4.20))
            ip = float(stats.get("inningsPitched", 0.1))
            hr = int(stats.get("homeRuns", 0))
            bb = int(stats.get("baseOnBalls", 0))
            k = int(stats.get("strikeOuts", 0))
            bf = int(stats.get("battersFaced", 1))
            wins = int(stats.get("wins", 0))
            losses = int(stats.get("losses", 0))

            if bf > 0:
                k_bb_pct = round((k / bf) - (bb / bf), 3)
                k_pct = k / bf
                bb_pct = bb / bf
            else:
                k_bb_pct = 0.0
                k_pct = 0.20
                bb_pct = 0.08

            if ip > 0:
                fip = round(
                    max(
                        0.0, (((13 * hr) + (3 * bb) - (2 * k)) / ip) + self.fip_constant
                    ),
                    2,
                )
                expected_hr = (hr * 0.5) + ((ip * 1.15 / 9.0) * 0.5)
                xfip = round(
                    max(
                        0.0, (((13 * expected_hr) + (3 * bb) - (2 * k)) / ip) + self.fip_constant
                    ),
                    2,
                )
            else:
                fip = era
                xfip = era

            xera = round(max(1.5, min(7.5, 3.10 + 12.0 * bb_pct - 15.0 * k_pct)), 2)
            xera = round(xera * 0.7 + era * 0.3, 2)

            pitcher_library[name] = {
                "era": era,
                "fip": fip,
                "xera": xera,
                "xfip": xfip,
                "k_bb_pct": k_bb_pct,
                "throws": throws,
                "innings_pitched": ip,
                "wins": wins,
                "losses": losses,
                "record": f"{wins}-{losses}",
            }
            print(f"✅ Başarılı (W-L: {wins}-{losses} | FIP: {fip})")

        output_path = os.path.join(self.data_dir, "pitcher_stats.json")
        history_dir = os.path.join(self.data_dir, "history")
        os.makedirs(history_dir, exist_ok=True)
        history_path = os.path.join(
            history_dir, f"{datetime.now().strftime('%Y-%m-%d')}_pitchers.json"
        )

        if pitcher_library:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, self._atomic_save, output_path, pitcher_library
            )
            await loop.run_in_executor(
                None, self._atomic_save, history_path, pitcher_library
            )
            print(
                f"\n🎉 GÖREV TAMAM! {len(pitcher_library)} atıcının verileri güvenle kaydedildi."
            )
        else:
            print("\n⚠️ Uyarı: Hiçbir atıcı verisi bulunamadı, JSON güncellenmedi.")


if __name__ == "__main__":
    scraper = PitcherScraper()
    scraper.build_pitcher_library()

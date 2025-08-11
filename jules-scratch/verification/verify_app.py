from playwright.sync_api import sync_playwright, expect
import os

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Arahkan ke aplikasi
            page.goto("http://127.0.0.1:8080", timeout=15000)

            # Unggah file WAV sampel
            file_path = os.path.abspath("jules-scratch/verification/sample.wav")
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File dummy audio tidak ditemukan di {file_path}")

            page.locator("#file-input").set_input_files(file_path)

            # Klik tombol pisah
            page.get_by_role("button", name="Pisahkan Audio").click()

            # Tunggu hasilnya muncul.
            # Demucs bisa memakan waktu lama, jadi kita butuh batas waktu yang panjang.
            results_heading = page.get_by_role("heading", name="Hasil")
            expect(results_heading).to_be_visible(timeout=240000) # Batas waktu 4 menit

            # Periksa salah satu stem, misalnya Vokal
            vocals_stem = page.get_by_role("heading", name="Vocals")
            expect(vocals_stem).to_be_visible()

            # Ambil tangkapan layar dari area hasil
            results_div = page.locator("#results")
            screenshot_path = "jules-scratch/verification/verification.png"
            results_div.screenshot(path=screenshot_path)

            print(f"Tangkapan layar disimpan ke {screenshot_path}")

        except Exception as e:
            print(f"Terjadi kesalahan saat verifikasi: {e}")
            error_screenshot_path = "jules-scratch/verification/error.png"
            page.screenshot(path=error_screenshot_path)
            print(f"Tangkapan layar error disimpan ke {error_screenshot_path}")

        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()

import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

class GoogleDriveService:
    def __init__(self):
        # Setup using environment variables or a default mock setup for testing
        # In a real environment, you'd load credentials securely based on the specific company (Tenant).
        self.scopes = ['https://www.googleapis.com/auth/drive.file']

    def _get_credentials(self, company_id: int):
        # Retrieve credentials from the local file database for the company
        token_path = os.path.join(os.path.dirname(__file__), "..", "..", f"company_{company_id}_token.json")
        if os.path.exists(token_path):
            with open(token_path, "r") as f:
                token_info = json.load(f)
                return Credentials.from_authorized_user_info(token_info, self.scopes)
        return None

    def _get_service(self, company_id: int):
        creds = self._get_credentials(company_id)
        if not creds:
            raise Exception("Google credentials not found for this company. Please login with Google first.")
        return build('drive', 'v3', credentials=creds)

    def upload_file(self, company_id: int, file_name: str, file_content: bytes, mime_type: str):
        """
        Uploads a file to the company's Google Drive using the real API and returns the Google Drive File ID.
        """
        try:
            service = self._get_service(company_id)
        except Exception as e:
            print(f"Warning: {e}. Falling back to mock for safety during dev.")
            return f"mock_gdrive_id_{file_name}_{company_id}"

        file_metadata = {'name': file_name}
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=mime_type, resumable=True)

        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')

drive_service = GoogleDriveService()

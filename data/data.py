# data/data.py - 위스키 앱 데이터 관리 시스템 (한남/충무로 분리 + 통계 자동 저장 + 가중치 분석)
import os
import json
import datetime
from typing import Dict, Any, List, Optional
import threading
import requests  # HF Space API 호출용

# 외부 라이브러리
import gspread
from google.oauth2.service_account import Credentials
import pytz

# === Kiwi 싱글톤 (메모리 최적화 + Thread Safe) ===
_KIWI_INSTANCE = None
_KIWI_LOCK = threading.Lock()

def _get_kiwi():
    """Kiwi 싱글톤 인스턴스 반환 (Thread Safe)"""
    global _KIWI_INSTANCE
    if _KIWI_INSTANCE is None:
        with _KIWI_LOCK:  # 동시 접근 방지
            if _KIWI_INSTANCE is None:  # Double-checked locking
                try:
                    from kiwipiepy import Kiwi
                    _KIWI_INSTANCE = Kiwi()
                    Logger.info("Kiwi 인스턴스 생성 완료 (Thread Safe)")
                except ImportError:
                    Logger.warning("kiwipiepy 설치 필요")
                    return None
    return _KIWI_INSTANCE

# === 불용어 목록 (전역 상수) ===
STOPWORDS = {
    # 일반 표현
    '느낌', '향', '맛', '노트', '스타일', '계열', '타입', '이미지', '캐릭터', 
    '밸런스', '구성', '전반', '전체', '기본', '일반적', '평범', '무난',
    '바탕', '하프', '고인', '피니시', '숙성', '기분', '사이', '마무리',
    '도수', '코리아', '위스키', '아드벡',
    # 정도 부사
    '조금', '약간', '매우', '너무', '꽤', '상당히', '살짝', 
    '강한', '약한', '진한', '연한', '가벼운', '묵직한',
    # 평가 표현
    '좋음', '별로', '괜찮', '싫음', '애매', '실망', '만족', '불호', 
    '호불호', '취향', '비추', '추천',
    # 상업적 표현
    '가성비', '가격', '비쌈', '저렴', '구매', '재구매', '선물', 
    '데일리', '입문', '초보', '고급', '한정', '에디션',
    # 시간/빈도
    '처음', '마지막', '이번', '예전', '요즘', '항상', '가끔', '자주',
    # 주관적 표현
    '기대', '생각', '느껴짐', '같음',
    # 조사/어미
    '의', '을', '를', '이', '가', '은', '는', '에', '에서', '로', '으로',
    '하다', '되다', '있다', '없다', '같다',
    # 추가
    '올라오', '기반', '비하', '누르', '느끼'
}

# === 설정 상수 ===
class Config:
    """앱 설정 상수"""
    SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")
    KEY_PATH = os.environ.get("GOOGLE_KEY_PATH", "")
    
    if not SHEET_ID:
        print("⚠️ GOOGLE_SHEET_ID 환경 변수 필요 - Railway Variables에 설정하세요")
    
    TASTE_NOTES = [
        "프루티", "플로럴", "스윗", "우디", "너티", 
        "피트", "스모키", "스파이시"
    ]
    
    # 별점 가중치
    RATING_WEIGHTS = {
        5: 1.0,
        4: 0.8,
        3: 0.6,
        2: 0.3,
        1: 0.1
    }

# === 글로벌 변수 ===
TASTE_NOTES = Config.TASTE_NOTES
RATING_WEIGHTS = Config.RATING_WEIGHTS

# 메모리 저장소
memory_store = {
    'records': [],
    'kakao_users': {},
    'hannam_products': [],
    'chungmuro_products': []
}

# Google Sheets Manager (Lazy Loading)
_sheets_manager_instance = None

def get_sheets_manager():
    """Google Sheets Manager 싱글톤 (Lazy Loading)"""
    global _sheets_manager_instance
    if _sheets_manager_instance is None:
        _sheets_manager_instance = GoogleSheetsManager()
    return _sheets_manager_instance

# === 유틸리티 클래스 ===
class Logger:
    """로깅 유틸리티"""
    @staticmethod
    def info(message: str): print(f"[INFO] {message}")
    @staticmethod
    def success(message: str): print(f"[SUCCESS] {message}")
    @staticmethod
    def warning(message: str): print(f"[WARNING] {message}")
    @staticmethod
    def error(message: str): print(f"[ERROR] {message}")
    @staticmethod
    def debug(message: str): print(f"[DEBUG] {message}")

class GoogleAuth:
    """Google 서비스 인증 관리"""
    @staticmethod
    def get_credentials(scopes: List[str]) -> Optional[Credentials]:
        """Google 인증 정보 가져오기"""
        # 1. 환경 변수에서 JSON 읽기 (Railway/Heroku)
        credentials_json = os.environ.get("GOOGLE_CREDENTIALS")
        if credentials_json:
            try:
                credentials_info = json.loads(credentials_json)
                Logger.success("환경 변수에서 Google 인증 정보 로드")
                return Credentials.from_service_account_info(credentials_info, scopes=scopes)
            except json.JSONDecodeError as e:
                Logger.error(f"환경변수 JSON 파싱 실패: {e}")

        # 2. 로컬 파일에서 읽기 (개발 환경)
        if Config.KEY_PATH and os.path.exists(Config.KEY_PATH):
            Logger.success(f"로컬 파일에서 Google 인증 정보 로드: {Config.KEY_PATH}")
            return Credentials.from_service_account_file(Config.KEY_PATH, scopes=scopes)

        Logger.error("Google 인증 정보를 찾을 수 없음 - GOOGLE_CREDENTIALS 환경 변수를 설정하세요")
        return None

# === Google Sheets 관리 ===
class GoogleSheetsManager:
    def __init__(self):
        self.sheet = None
        self.whiskey_worksheet = None
        self.users_worksheet = None
        self.hannam_menu_worksheet = None
        self.chungmuro_menu_worksheet = None
        self.is_connected = False
        self._connect()

    def _connect(self) -> bool:
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = GoogleAuth.get_credentials(scopes)
            if not creds:
                Logger.warning("Google 인증 실패")
                return False
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(Config.SHEET_ID)
            
            # 위스키 기록용 시트
            try:
                self.whiskey_worksheet = self.sheet.worksheet("아카이빙")
                Logger.success("기존 '아카이빙' 시트 연결")
            except gspread.WorksheetNotFound:
                self.whiskey_worksheet = self.sheet.add_worksheet(title="아카이빙", rows="1000", cols="10")
                Logger.success("새 '아카이빙' 시트 생성")
            self._setup_whiskey_headers()
            
            # 사용자 관리용 시트
            try:
                self.users_worksheet = self.sheet.worksheet("users")
                Logger.success("기존 'users' 시트 연결")
            except gspread.WorksheetNotFound:
                self.users_worksheet = self.sheet.add_worksheet(title="users", rows="1000", cols="10")
                Logger.success("새 'users' 시트 생성")
            self._setup_users_headers()
            
            # 한남메뉴판 시트 연결
            try:
                self.hannam_menu_worksheet = self.sheet.worksheet("한남메뉴판")
                Logger.success("기존 '한남메뉴판' 시트 연결")
            except gspread.WorksheetNotFound:
                Logger.warning("'한남메뉴판' 시트를 찾을 수 없음")
                self.hannam_menu_worksheet = None
            
            # 충무로 메뉴판 시트 연결
            try:
                self.chungmuro_menu_worksheet = self.sheet.worksheet("충무로 메뉴판")
                Logger.success("기존 '충무로 메뉴판' 시트 연결")
            except gspread.WorksheetNotFound:
                Logger.warning("'충무로 메뉴판' 시트를 찾을 수 없음")
                self.chungmuro_menu_worksheet = None
            
            self.is_connected = True
            Logger.success("Google Sheets 연결 완료")
            return True
        except Exception as e:
            Logger.warning(f"Google Sheets 연결 실패: {e}")
            return False

    def _setup_whiskey_headers(self):
        """위스키 기록 시트 헤더 설정"""
        try:
            values = self.whiskey_worksheet.get_all_values()
            if not values or not values[0]:
                headers = [
                    'timestamp', 'date', 'user_id', 'username', 
                    'whiskey_name', 'ocr_text', 'taste_notes', 'rating', 'memo', 'keyword'
                ]
                self.whiskey_worksheet.update('A1:J1', [headers])
                Logger.success("위스키 시트 헤더 설정 완료")
        except Exception as e:
            Logger.error(f"위스키 시트 설정 실패: {e}")

    def _setup_users_headers(self):
        """사용자 관리 시트 헤더 설정"""
        try:
            values = self.users_worksheet.get_all_values()
            if not values or not values[0]:
                headers = [
                    'user_id', 'username', 'nickname', 'email', 'login_type', 
                    'created_at', 'last_login', 'total_records', 'avg_rating'
                ]
                self.users_worksheet.update('A1:I1', [headers])
                Logger.success("사용자 시트 헤더 설정 완료")
        except Exception as e:
            Logger.error(f"사용자 시트 설정 실패: {e}")

    def _get_products_from_sheet(self, worksheet) -> List[str]:
        """특정 시트에서 제품명 가져오기"""
        if not worksheet:
            return []
        
        try:
            values = worksheet.get_all_values()
            if len(values) <= 1:
                return []
            
            headers = values[0]
            product_col_idx = None
            
            for idx, header in enumerate(headers):
                if '제품명' in header:
                    product_col_idx = idx
                    break
            
            if product_col_idx is None:
                Logger.error(f"'제품명' 컬럼을 찾을 수 없음")
                return []
            
            products = []
            for row in values[1:]:
                if len(row) > product_col_idx and row[product_col_idx].strip():
                    products.append(row[product_col_idx].strip())
            
            return products
            
        except Exception as e:
            Logger.error(f"제품명 조회 실패: {e}")
            return []

    def get_hannam_products(self) -> List[str]:
        """한남메뉴판 제품명"""
        if not self.is_connected:
            return []
        products = self._get_products_from_sheet(self.hannam_menu_worksheet)
        Logger.success(f"한남 제품명 {len(products)}개 로드")
        return products

    def get_chungmuro_products(self) -> List[str]:
        """충무로 메뉴판 제품명"""
        if not self.is_connected:
            return []
        products = self._get_products_from_sheet(self.chungmuro_menu_worksheet)
        Logger.success(f"충무로 제품명 {len(products)}개 로드")
        return products

    def get_existing_user(self, user_id: str) -> Optional[Dict]:
        """기존 사용자 조회"""
        if not self.is_connected or not self.users_worksheet:
            return None
        try:
            values = self.users_worksheet.get_all_values()
            if len(values) <= 1:
                return None
            
            for row in values[1:]:
                if len(row) > 0 and row[0] == user_id:
                    return {
                        'user_id': row[0] if len(row) > 0 else '',
                        'username': row[1] if len(row) > 1 else '',
                        'nickname': row[2] if len(row) > 2 else '',
                        'email': row[3] if len(row) > 3 else '',
                        'login_type': row[4] if len(row) > 4 else '',
                        'created_at': row[5] if len(row) > 5 else '',
                        'last_login': row[6] if len(row) > 6 else '',
                        'total_records': int(row[7]) if len(row) > 7 and row[7].isdigit() else 0,
                        'avg_rating': float(row[8]) if len(row) > 8 and row[8] else 0.0
                    }
            return None
        except Exception as e:
            Logger.error(f"사용자 조회 실패: {e}")
            return None

    def save_user(self, user_data: Dict[str, Any], total_records: int = 0, avg_rating: float = 0.0) -> bool:
        """사용자 저장 또는 업데이트 - 통계 포함"""
        if not self.is_connected or not self.users_worksheet:
            return False
        try:
            values = self.users_worksheet.get_all_values()
            existing_row = None
            
            if len(values) > 1:
                for i, row in enumerate(values[1:], start=2):
                    if len(row) > 0 and row[0] == user_data["user_id"]:
                        existing_row = i
                        break
            
            if existing_row:
                # 기존 사용자: 최종로그인 + 통계 업데이트
                self.users_worksheet.update(f'G{existing_row}:I{existing_row}', 
                    [[user_data["last_login"], total_records, avg_rating]])
                Logger.success(f"사용자 통계 업데이트: {user_data['username']} (기록: {total_records}, 평점: {avg_rating})")
            else:
                # 신규 사용자: 전체 데이터 저장
                row_data = [
                    user_data["user_id"],
                    user_data["username"], 
                    user_data["nickname"],
                    user_data.get("email", ""),
                    user_data["login_type"],
                    user_data["created_at"],
                    user_data["last_login"],
                    total_records,
                    avg_rating
                ]
                self.users_worksheet.append_row(row_data)
                Logger.success(f"새 사용자 저장: {user_data['username']}")
            
            return True
        except Exception as e:
            Logger.error(f"사용자 저장 실패: {e}")
            return False

    def save_whiskey_record(self, record: Dict[str, Any]) -> bool:
        """위스키 기록 저장"""
        if not self.is_connected or not self.whiskey_worksheet:
            return False
        try:
            taste_notes_str = ", ".join(record.get('taste_notes', []))
            row_data = [
                record.get('timestamp', ''),
                record.get('date', ''),
                record.get('user_id', ''),
                record.get('username', ''),
                record.get('whiskey_name', ''),
                '',  # ocr_text (NULL)
                taste_notes_str,
                record.get('rating', 0),
                record.get('memo', '')
            ]
            values = self.whiskey_worksheet.get_all_values()
            next_row = len(values) + 1
            range_name = f'A{next_row}:I{next_row}'
            self.whiskey_worksheet.update(range_name, [row_data])
            Logger.success(f"기록 저장: {record.get('whiskey_name')}")
            return True
        except Exception as e:
            Logger.error(f"기록 저장 실패: {e}")
            return False

    def update_whiskey_record(self, record: Dict[str, Any]) -> bool:
        """위스키 기록 수정"""
        if not self.is_connected or not self.whiskey_worksheet:
            return False
        try:
            values = self.whiskey_worksheet.get_all_values()
            if len(values) <= 1:
                return False
            
            target_row = None
            record_id = str(record.get('id', record.get('timestamp', '')))
            
            for i, row in enumerate(values[1:], start=2):
                if len(row) > 0 and str(row[0]) == record_id:
                    target_row = i
                    break
            
            if not target_row:
                Logger.error(f"수정할 레코드를 찾을 수 없음: {record_id}")
                return False
            
            taste_notes_str = ", ".join(record.get('taste_notes', []))
            row_data = [
                record.get('timestamp', ''),
                record.get('date', ''),
                record.get('user_id', ''),
                record.get('username', ''),
                record.get('whiskey_name', ''),
                '',  # ocr_text (NULL)
                taste_notes_str,
                record.get('rating', 0),
                record.get('memo', '')
            ]
            
            range_name = f'A{target_row}:I{target_row}'
            self.whiskey_worksheet.update(range_name, [row_data])
            Logger.success(f"기록 수정 완료: {record.get('whiskey_name')}")
            return True
            
        except Exception as e:
            Logger.error(f"기록 수정 실패: {e}")
            return False

    def soft_delete_whiskey_record(self, record_id: str, user_id: str) -> bool:
        """위스키 기록 Soft Delete"""
        if not self.is_connected or not self.whiskey_worksheet:
            return False
        try:
            values = self.whiskey_worksheet.get_all_values()
            if len(values) <= 1:
                return False
            
            target_row = None
            for i, row in enumerate(values[1:], start=2):
                if len(row) > 2 and str(row[0]) == str(record_id) and str(row[2]) == str(user_id):
                    target_row = i
                    break
            
            if not target_row:
                Logger.error(f"삭제할 레코드를 찾을 수 없음: {record_id}")
                return False
            
            current_row = values[target_row - 1]
            current_memo = current_row[8] if len(current_row) > 8 else ""
            
            kst = pytz.timezone('Asia/Seoul')
            deleted_at = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M")
            new_memo = f"[삭제됨 {deleted_at}] {current_memo}"
            
            self.whiskey_worksheet.update(f'I{target_row}', [[new_memo]])
            Logger.success(f"Soft Delete 완료: {record_id}")
            return True
            
        except Exception as e:
            Logger.error(f"Soft Delete 실패: {e}")
            return False
    

    def get_all_whiskey_records(self) -> List[Dict[str, Any]]:
        """모든 위스키 기록 조회"""
        if not self.is_connected or not self.whiskey_worksheet:
            return []
        try:
            values = self.whiskey_worksheet.get('A:J')  # I → J로 변경
            if len(values) <= 1:
                return []
            records = []
            for row in values[1:]:
                if not any(row):
                    continue
                record = self._parse_whiskey_row(row)
                records.append(record)
            records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            Logger.success(f"전체 {len(records)}개 기록 로드")
            return records
        except Exception as e:
            Logger.error(f"기록 조회 실패: {e}")
            return []

    def get_user_whiskey_records(self, user_id: str) -> List[Dict[str, Any]]:
        """특정 사용자의 위스키 기록 조회"""
        if not self.is_connected or not self.whiskey_worksheet:
            return []
        try:
            all_records = self.get_all_whiskey_records()
            user_records = [r for r in all_records if r.get('user_id') == user_id]
            Logger.success(f"사용자 {user_id}의 기록 {len(user_records)}개 조회")
            return user_records
        except Exception as e:
            Logger.error(f"사용자 기록 조회 실패: {e}")
            return []

    def get_user_whiskey_records_visible(self, user_id: str) -> List[Dict[str, Any]]:
        """특정 사용자의 위스키 기록 조회 (삭제되지 않은 것만)"""
        if not self.is_connected or not self.whiskey_worksheet:
            return []
        try:
            all_records = self.get_user_whiskey_records(user_id)
            visible_records = []
            for record in all_records:
                memo = record.get('memo', '')
                if not memo.startswith('[삭제됨'):
                    visible_records.append(record)
            
            Logger.success(f"사용자 {user_id}의 활성 기록 {len(visible_records)}개 조회")
            return visible_records
        except Exception as e:
            Logger.error(f"활성 기록 조회 실패: {e}")
            return []

    def _parse_whiskey_row(self, row: List[str]) -> Dict[str, Any]:
        """위스키 기록 행 파싱"""
        row = (row + [''] * 10)[:10]  # 9 → 10으로 변경
        taste_notes = []
        if row[6]:
            taste_notes = [note.strip() for note in row[6].split(',') if note.strip()]
        return {
            'id': row[0],
            'timestamp': row[0],
            'date': row[1], 
            'user_id': row[2],
            'username': row[3],
            'whiskey_name': row[4],
            'taste_notes': taste_notes,
            'rating': int(row[7]) if (row[7] or '').isdigit() else 0,
            'memo': row[8],
            'keyword': row[9] if len(row) > 9 else ''
        }

# === 위스키 데이터 관리 ===
class WhiskeyDataManager:
    def __init__(self):
        # Google Sheets는 필요할 때만 연결 (Lazy Loading)
        self._sheets_manager = None
    
    @property
    def sheets_manager(self):
        """Lazy Loading으로 Google Sheets Manager 반환"""
        if self._sheets_manager is None:
            self._sheets_manager = get_sheets_manager()
        return self._sheets_manager

    def get_hannam_products(self) -> List[str]:
        """한남 제품명 목록 (캐싱)"""
        if memory_store.get('hannam_products'):
            return memory_store['hannam_products']
        
        products = self.sheets_manager.get_hannam_products()
        memory_store['hannam_products'] = products
        return products

    def get_chungmuro_products(self) -> List[str]:
        """충무로 제품명 목록 (캐싱)"""
        if memory_store.get('chungmuro_products'):
            return memory_store['chungmuro_products']
        
        products = self.sheets_manager.get_chungmuro_products()
        memory_store['chungmuro_products'] = products
        return products

    def save_record(self, record: Dict[str, Any]) -> bool:
        try:
            success = self.sheets_manager.save_whiskey_record(record)
            self._save_to_memory(record)
            return success
        except Exception as e:
            Logger.error(f"기록 저장 실패: {e}")
            self._save_to_memory(record)
            return False

    def update_record(self, record: Dict[str, Any]) -> bool:
        try:
            success = self.sheets_manager.update_whiskey_record(record)
            if 'records' in memory_store:
                record_id = str(record.get('id', record.get('timestamp', '')))
                for i, mem_record in enumerate(memory_store['records']):
                    mem_id = str(mem_record.get('id', mem_record.get('timestamp', '')))
                    if mem_id == record_id:
                        memory_store['records'][i] = record
                        break
            return success
        except Exception as e:
            Logger.error(f"기록 수정 실패: {e}")
            return False

    def soft_delete_record(self, record_id: str, user_id: str) -> bool:
        try:
            success = self.sheets_manager.soft_delete_whiskey_record(record_id, user_id)
            if 'records' in memory_store:
                for record in memory_store['records']:
                    rec_id = str(record.get('id', record.get('timestamp', '')))
                    if rec_id == str(record_id) and record.get('user_id') == user_id:
                        kst = pytz.timezone('Asia/Seoul')
                        deleted_at = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M")
                        record['memo'] = f"[삭제됨 {deleted_at}] {record.get('memo', '')}"
                        break
            return success
        except Exception as e:
            Logger.error(f"Soft Delete 실패: {e}")
            return False
    

    def _save_to_memory(self, record: Dict[str, Any]):
        if 'records' not in memory_store:
            memory_store['records'] = []
        if record not in memory_store['records']:
            memory_store['records'].append(record)

    def get_all_records(self) -> List[Dict[str, Any]]:
        try:
            if self.sheets_manager.is_connected:
                sheets_records = self.sheets_manager.get_all_whiskey_records()
                if sheets_records:
                    return sheets_records
            memory_records = list(memory_store.get('records', []))
            memory_records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return memory_records
        except Exception as e:
            Logger.error(f"기록 조회 실패: {e}")
            return list(memory_store.get('records', []))

    def get_user_records(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            if self.sheets_manager.is_connected:
                sheets_records = self.sheets_manager.get_user_whiskey_records_visible(user_id)
                if sheets_records:
                    return sheets_records
            
            all_records = self.get_all_records()
            user_records = []
            for record in all_records:
                record_user_id = record.get('user_id', '').strip()
                memo = record.get('memo', '')
                if record_user_id == user_id and not memo.startswith('[삭제됨'):
                    user_records.append(record)
            
            return user_records
        except Exception as e:
            Logger.error(f"사용자 기록 조회 실패: {e}")
            return []

    def get_user_records_count(self, user_id: str) -> int:
        try:
            user_records = self.get_user_records(user_id)
            return len(user_records)
        except Exception as e:
            Logger.error(f"기록 개수 조회 실패: {e}")
            return 0

# === 전역 인스턴스 ===
data_manager = WhiskeyDataManager()

# === 외부 API 함수 ===
def get_existing_user(user_id: str) -> Optional[Dict]:
    return data_manager.sheets_manager.get_existing_user(user_id)

def save_kakao_user(user_data: Dict[str, Any]) -> bool:
    """카카오 사용자 저장 - 로그인 시 통계 자동 계산 및 저장"""
    try:
        # 사용자의 현재 기록 통계 계산
        user_records = get_user_records(user_data['user_id'])
        total_records = len(user_records)
        avg_rating = (
            sum(r.get('rating', 0) for r in user_records) / total_records
            if total_records > 0 else 0.0
        )
        
        Logger.info(f"로그인 통계 계산: {user_data['username']} - 기록 {total_records}개, 평점 {avg_rating:.1f}")
        
        # 통계와 함께 users 시트에 저장
        success = data_manager.sheets_manager.save_user(
            user_data, 
            total_records, 
            round(avg_rating, 1)
        )
        
        memory_store['kakao_users'][user_data['user_id']] = user_data
        return success
    except Exception as e:
        Logger.error(f"사용자 저장 실패: {e}")
        return False

def save_whiskey_record(record: Dict[str, Any]) -> bool:
    return data_manager.save_record(record)

def update_whiskey_record(record: Dict[str, Any]) -> bool:
    return data_manager.update_record(record)

def soft_delete_record(record_id: str, user_id: str) -> bool:
    return data_manager.soft_delete_record(record_id, user_id)

def get_user_records(user_id: str) -> List[Dict[str, Any]]:
    return data_manager.get_user_records(user_id)

def get_user_records_count(user_id: str) -> int:
    return data_manager.get_user_records_count(user_id)

def get_records_for_display(user_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    if user_data and isinstance(user_data, dict) and user_data.get('user_id'):
        return data_manager.get_user_records(user_data['user_id'])
    return data_manager.get_all_records()

def get_hannam_products() -> List[str]:
    """한남 제품명 목록"""
    return data_manager.get_hannam_products()

def get_chungmuro_products() -> List[str]:
    """충무로 제품명 목록"""
    return data_manager.get_chungmuro_products()

def update_user_stats(user_id: str) -> bool:
    """사용자 통계 업데이트 (기록 저장/삭제 시 호출)"""
    try:
        user_data = data_manager.sheets_manager.get_existing_user(user_id)
        if not user_data:
            Logger.warning(f"사용자를 찾을 수 없음: {user_id}")
            return False
        
        # 통계 계산 (visible 기록만)
        records = get_user_records(user_id)
        total_records = len(records)
        avg_rating = (
            sum(r.get('rating', 0) for r in records) / total_records 
            if total_records > 0 else 0.0
        )
        
        # last_login 업데이트
        kst = pytz.timezone('Asia/Seoul')
        user_data['last_login'] = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        
        # users 시트에 통계 저장
        success = data_manager.sheets_manager.save_user(user_data, total_records, round(avg_rating, 1))
        
        if success:
            Logger.success(f"사용자 통계 업데이트 완료: {user_id} (기록: {total_records}, 평점: {avg_rating:.1f})")
        
        return success
        
    except Exception as e:
        Logger.error(f"사용자 통계 업데이트 실패: {e}")
        return False


# ===== 가중치 기반 분석 함수 =====

def _note_to_korean(note: str) -> str:
    """영문 노트 → 한글 변환"""
    mapping = {
        "fruity": "프루티",
        "floral": "플로럴",
        "sweet": "스윗",
        "oaky": "우디",
        "nutty": "너티",
        "peaty": "피트",
        "smoky": "스모키",
        "spicy": "스파이시"
    }
    return mapping.get(note, note)


# === 화이트리스트 로드 ===
_WHITELIST = None
_WHITELIST_LOCK = threading.Lock()

def _get_whitelist():
    """화이트리스트 싱글톤 로드 (pandas 없이)"""
    global _WHITELIST
    if _WHITELIST is None:
        with _WHITELIST_LOCK:
            if _WHITELIST is None:
                try:
                    import csv
                    whitelist_path = os.path.join(os.path.dirname(__file__), 'whiskey_whitelist.csv')
                    if os.path.exists(whitelist_path):
                        with open(whitelist_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            _WHITELIST = set(row['word'] for row in reader)
                        Logger.info(f"화이트리스트 로드 완료: {len(_WHITELIST)}개 단어")
                    else:
                        Logger.warning(f"화이트리스트 파일 없음: {whitelist_path}")
                        _WHITELIST = set()
                except Exception as e:
                    Logger.error(f"화이트리스트 로드 실패: {e}")
                    _WHITELIST = set()
    return _WHITELIST


def _parse_memo_text(memo_list: List[str]) -> Dict[str, int]:
    """
    memo 텍스트를 파싱해서 명사/동사 추출 (Kiwi 싱글톤 사용)
    + 화이트리스트 필터 적용
    
    Args:
        memo_list: memo 텍스트 리스트
    
    Returns:
        {단어: 빈도} 딕셔너리 (화이트리스트에 있는 표현만)
    """
    try:
        # Kiwi 싱글톤 사용
        kiwi = _get_kiwi()
        if kiwi is None:
            return {}
        
        # 화이트리스트 로드
        whitelist = _get_whitelist()
        
        word_counts = {}
        
        for memo in memo_list:
            if not memo or memo.startswith('[삭제됨'):
                continue
            
            # 형태소 분석
            result = kiwi.analyze(memo)
            
            for token in result[0][0]:
                # 명사(NNG, NNP) 또는 동사(VV)만 추출
                if token.tag in ['NNG', 'NNP', 'VV']:
                    word = token.form
                    # 1글자 제외 + 불용어 제외 + 화이트리스트 체크
                    if len(word) > 1 and word not in STOPWORDS and word in whitelist:
                        word_counts[word] = word_counts.get(word, 0) + 1
        
        Logger.info(f"워드클라우드: {len(word_counts)}개 단어 추출 (화이트리스트 필터)")
        return word_counts
        
    except Exception as e:
        Logger.error(f"memo 파싱 실패: {e}")
        return {}


def analyze_recent_taste_trend(user_id: str, n: int = 10) -> Optional[Dict[str, Any]]:
    """
    최근 N개 기록에서 트렌드 분석 (가중치 적용)
    
    조건:
    - ★★★ 이상만 반영 (rating >= 3)
    - 가중치 적용: ★★★★★(1.0), ★★★★(0.8), ★★★(0.6)
    - 1위가 2위보다 1.5배 이상이면 "자주 사용"
    
    Returns:
        None: 분석 불가 (기록 부족)
        {
            'is_clear_trend': False
        }
        또는
        {
            'is_clear_trend': True,
            'top_note': 'spicy',
            'top_note_korean': '스파이시'
        }
    """
    try:
        records = get_user_records(user_id)
        
        if len(records) < 5:
            Logger.warning(f"분석 최소 기준 미달: {len(records)}개 (최소 5개 필요)")
            return None
        
        # 최근 N개만 추출
        recent_records = records[:min(n, len(records))]
        
        # ★★★ 이상만 필터링
        filtered_records = [r for r in recent_records if r.get('rating', 0) >= 3]
        
        if not filtered_records:
            Logger.warning(f"★★★ 이상 기록이 없음")
            return None
        
        # 가중치 적용 빈도 계산
        weighted_counts = {}
        for record in filtered_records:
            rating = record.get('rating', 3)
            weight = RATING_WEIGHTS.get(rating, 0.6)
            notes = record.get('taste_notes', [])
            
            for note in notes:
                weighted_counts[note] = weighted_counts.get(note, 0) + weight
        
        if not weighted_counts:
            return None
        
        # 빈도순 정렬
        sorted_notes = sorted(weighted_counts.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_notes) < 2:
            # 노트가 1개만 있으면 무조건 명확한 트렌드
            top_note = sorted_notes[0][0]
            return {
                'is_clear_trend': True,
                'top_note': top_note,
                'top_note_korean': _note_to_korean(top_note)
            }
        
        # 1위와 2위 비교 (1.5배 이상)
        first_score = sorted_notes[0][1]
        second_score = sorted_notes[1][1]
        
        if first_score >= second_score * 1.5:
            # 명확한 트렌드
            top_note = sorted_notes[0][0]
            Logger.success(f"명확한 트렌드: {top_note} ({first_score:.1f} vs {second_score:.1f})")
            return {
                'is_clear_trend': True,
                'top_note': top_note,
                'top_note_korean': _note_to_korean(top_note)
            }
        else:
            # 고르게 분포
            Logger.info(f"고른 분포: 1위 {first_score:.1f} vs 2위 {second_score:.1f}")
            return {
                'is_clear_trend': False
            }
        
    except Exception as e:
        Logger.error(f"최근 트렌드 분석 실패: {e}")
        return None


def get_user_taste_analysis(user_id: str) -> Optional[Dict[str, Any]]:
    """
    사용자 전체 취향 분석 (가중치 적용 + memo 워드클라우드) + 캐싱
    
    Returns:
        None: 분석 불가 (기록 5개 미만)
        {
            'main_expressions': {note: weighted_score},  # ★★★★ 이상
            'sub_expressions': {note: weighted_score},   # ★★ 이하
            'memo_wordcloud': {word: count},             # 본인 memo 워드클라우드
            'total_count': int
        }
    """
    try:
        # 캐시 확인
        cache_key = f"taste_analysis:{user_id}"
        try:
            from cache_utils import get_cache, set_cache
            cached = get_cache(cache_key)
            if cached is not None:
                Logger.info(f"캐시에서 취향 분석 로드: {user_id}")
                return cached
        except ImportError:
            pass  # 캐시 없으면 무시
        
        records = get_user_records(user_id)
        
        if len(records) < 5:
            Logger.warning(f"분석 최소 기준 미달: {len(records)}개 (최소 5개 필요)")
            return None
        
        # 주요 표현 (★★★★ 이상) vs 보조 표현 (★★ 이하)
        main_expressions = {}
        sub_expressions = {}
        memo_texts = []
        
        for record in records:
            rating = record.get('rating', 0)
            weight = RATING_WEIGHTS.get(rating, 0)
            notes = record.get('taste_notes', [])
            memo = record.get('memo', '')
            
            # memo 수집
            if memo and not memo.startswith('[삭제됨'):
                memo_texts.append(memo)
            
            for note in notes:
                if rating >= 4:
                    # ★★★★ 이상 → 주요 표현
                    main_expressions[note] = main_expressions.get(note, 0) + weight
                elif rating <= 2:
                    # ★★ 이하 → 보조 표현
                    sub_expressions[note] = sub_expressions.get(note, 0) + weight
        
        # memo 워드클라우드 생성
        memo_wordcloud = _parse_memo_text(memo_texts)
        
        result = {
            'main_expressions': main_expressions,
            'sub_expressions': sub_expressions,
            'memo_wordcloud': memo_wordcloud,
            'total_count': len(records)
        }
        
        # 캐시 저장
        try:
            set_cache(cache_key, result)
        except:
            pass
        
        Logger.success(f"취향 분석 완료: 주요 {len(main_expressions)}개, 보조 {len(sub_expressions)}개, 단어 {len(memo_wordcloud)}개")
        
        return result
        
    except Exception as e:
        Logger.error(f"취향 분석 실패: {e}")
        return None


def get_similar_users_memo_wordcloud(user_id: str, user_notes: List[str]) -> Dict[str, int]:
    """
    같은 taste_notes 조합을 가진 다른 사용자들의 memo 워드클라우드
    
    Args:
        user_id: 현재 사용자 ID
        user_notes: 현재 사용자의 주요 노트 리스트
    
    Returns:
        {단어: 빈도} 딕셔너리
    """
    try:
        if not user_notes:
            return {}
        
        # 전체 기록 가져오기
        all_records = data_manager.get_all_records()
        
        similar_memos = []
        user_notes_set = set(user_notes)
        
        for record in all_records:
            # 본인 제외
            if record.get('user_id') == user_id:
                continue
            
            # memo가 없으면 스킵
            memo = record.get('memo', '')
            if not memo or memo.startswith('[삭제됨'):
                continue
            
            # taste_notes 비교 (겹치는 게 있으면)
            record_notes = set(record.get('taste_notes', []))
            if record_notes & user_notes_set:  # 교집합이 있으면
                similar_memos.append(memo)
        
        if not similar_memos:
            Logger.info("유사 사용자 없음")
            return {}
        
        # 워드클라우드 생성
        wordcloud = _parse_memo_text(similar_memos)
        Logger.success(f"유사 사용자 {len(similar_memos)}개 memo 분석 완료")
        
        return wordcloud
        
    except Exception as e:
        Logger.error(f"유사 사용자 분석 실패: {e}")
        return {}


def get_product_reviews_wordcloud(user_id: str, whiskey_name: str) -> Dict[str, Any]:
    """
    특정 제품에 대한 다른 사용자들의 리뷰 워드클라우드
    
    Args:
        user_id: 현재 사용자 ID
        whiskey_name: 위스키 제품명
    
    Returns:
        {
            'wordcloud': {단어: 빈도},
            'count': 리뷰 개수,
            'has_data': 데이터 존재 여부
        }
    """
    try:
        # 전체 기록 가져오기
        all_records = data_manager.get_all_records()
        
        similar_memos = []
        
        for record in all_records:
            # 본인 제외
            if record.get('user_id') == user_id:
                continue
            
            # 제품명 매칭 (정확 매칭)
            if record.get('whiskey_name') != whiskey_name:
                continue
            
            # memo가 없으면 스킵
            memo = record.get('memo', '')
            if not memo or memo.startswith('[삭제됨'):
                continue
            
            similar_memos.append(memo)
        
        if not similar_memos:
            return {
                'wordcloud': {},
                'count': 0,
                'has_data': False
            }
        
        # 워드클라우드 생성
        wordcloud = _parse_memo_text(similar_memos)
        Logger.success(f"{whiskey_name} 제품 리뷰 {len(similar_memos)}개 분석 완료")
        
        return {
            'wordcloud': wordcloud,
            'count': len(similar_memos),
            'has_data': True
        }
        
    except Exception as e:
        Logger.error(f"제품 리뷰 분석 실패: {e}")
        return {
            'wordcloud': {},
            'count': 0,
            'has_data': False
        }


def debug_status():
    """시스템 상태 디버깅"""
    print("\n" + "="*50)
    print("위스키 데이터 시스템 상태")
    print("="*50)
    print(f"Google Sheets 연결: {'연결됨' if data_manager.sheets_manager.is_connected else '연결 안됨'}")
    print(f"등록된 사용자: {len(memory_store.get('kakao_users', {}))}명")
    all_records = data_manager.get_all_records()
    print(f"전체 기록: {len(all_records)}개")
    hannam = get_hannam_products()
    chungmuro = get_chungmuro_products()
    print(f"한남 제품: {len(hannam)}개")
    print(f"충무로 제품: {len(chungmuro)}개")
    print("="*50 + "\n")

if __name__ == "__main__":
    Logger.info("위스키 데이터 매니저 시작")
    debug_status()


def add_preferred_keyword(user_id: str, keyword: str) -> bool:
    """Users 시트에 선호 키워드 추가 (전반적 선호)"""
    try:
        sheets_manager = data_manager.sheets_manager
        if not sheets_manager.is_connected or not sheets_manager.users_worksheet:
            print(f"[ERROR] Users 시트 연결 안 됨")
            return False
        
        users_data = sheets_manager.users_worksheet.get_all_records()
        
        for i, user in enumerate(users_data, start=2):
            if user.get('user_id') == user_id:
                # keyword 컬럼 확인 (J열)
                current_keywords = user.get('keyword', '')
                
                # 중복 체크
                if current_keywords:
                    keywords_list = [k.strip() for k in current_keywords.split(',')]
                    if keyword in keywords_list:
                        print(f"[INFO] 이미 저장된 키워드: {keyword}")
                        return True  # 이미 있음
                    keywords_list.append(keyword)
                    new_keywords = ', '.join(keywords_list)
                else:
                    new_keywords = keyword
                
                # 업데이트 - J열 (10번째)
                sheets_manager.users_worksheet.update_cell(i, 10, new_keywords)
                print(f"[SUCCESS] 선호 키워드 추가 (Users): {user_id} - {keyword}")
                return True
        
        print(f"[ERROR] 사용자 없음: {user_id}")
        return False
        
    except Exception as e:
        print(f"[ERROR] 선호 키워드 추가 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def add_record_keyword(record_id: str, user_id: str, keyword: str) -> bool:
    """아카이빙 시트에 제품별 선호 키워드 추가"""
    try:
        sheets_manager = data_manager.sheets_manager
        if not sheets_manager.is_connected or not sheets_manager.whiskey_worksheet:
            print(f"[ERROR] 아카이빙 시트 연결 안 됨")
            return False
        
        values = sheets_manager.whiskey_worksheet.get_all_values()
        if len(values) <= 1:
            return False
        
        # 해당 기록 찾기
        target_row = None
        for i, row in enumerate(values[1:], start=2):
            if len(row) > 2 and str(row[0]) == str(record_id) and str(row[2]) == str(user_id):
                target_row = i
                break
        
        if not target_row:
            print(f"[ERROR] 기록을 찾을 수 없음: {record_id}")
            return False
        
        # 현재 키워드 가져오기
        current_row = values[target_row - 1]
        current_keywords = current_row[9] if len(current_row) > 9 else ""
        
        # 중복 체크 및 추가
        if current_keywords:
            keywords_list = [k.strip() for k in current_keywords.split(',')]
            if keyword in keywords_list:
                print(f"[INFO] 이미 저장된 키워드 (기록): {keyword}")
                return True
            keywords_list.append(keyword)
            new_keywords = ', '.join(keywords_list)
        else:
            new_keywords = keyword
        
        # 업데이트 - J열
        sheets_manager.whiskey_worksheet.update_cell(target_row, 10, new_keywords)
        print(f"[SUCCESS] 제품 키워드 추가 (아카이빙): {record_id} - {keyword}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 제품 키워드 추가 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_user_preferred_keywords(user_id: str) -> List[str]:
    """Users 시트에서 선호 키워드 가져오기"""
    try:
        sheets_manager = data_manager.sheets_manager
        if not sheets_manager.is_connected or not sheets_manager.users_worksheet:
            print(f"[ERROR] Users 시트 연결 안 됨")
            return []
        
        users_data = sheets_manager.users_worksheet.get_all_records()
        
        for user in users_data:
            if user.get('user_id') == user_id:
                # keyword 컬럼 확인 (J열)
                keywords = user.get('keyword', '')
                if keywords:
                    return [k.strip() for k in keywords.split(',')]
                return []
        
        return []
        
    except Exception as e:
        print(f"[ERROR] 선호 키워드 조회 실패: {e}")
        return []
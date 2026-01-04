# app.py - OAuth REST API 방식 카카오 로그인
import dash
from dash import html, dcc
import os
from flask import request, jsonify, session, redirect
import json
import datetime
import random
import requests
import pytz

from components.layouts import get_main_layout
from components.callbacks import register_callbacks
from data.data import save_kakao_user, get_existing_user

# ===== 카카오 OAuth 설정 =====
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY")
KAKAO_REDIRECT_URI = os.environ.get("KAKAO_REDIRECT_URI")

if not KAKAO_REST_API_KEY:
    print("⚠️ KAKAO_REST_API_KEY 환경 변수 필요")
if not KAKAO_REDIRECT_URI:
    print("⚠️ KAKAO_REDIRECT_URI 환경 변수 필요")

print(f"[카카오 설정] REST API KEY: {KAKAO_REST_API_KEY[:10] if KAKAO_REST_API_KEY else 'None'}...")
print(f"[카카오 설정] REDIRECT URI: {KAKAO_REDIRECT_URI or 'None'}")

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Flask 세션 시크릿 키 설정
server.secret_key = os.environ.get('SECRET_KEY', 'kH9mP2nQ5rT8vW1yE4xB7cF0jG3sL6aD9uN2zK5hM8pR1tY4wX7vC0fJ3gL6sN9q')

# ===== 헬스체크 엔드포인트 =====

@server.route('/health')
def health_check():
    """Railway 헬스체크 전용 - 즉시 응답"""
    return jsonify({
        'status': 'ok',
        'service': 'tentlog',
        'version': '1.0.0'
    }), 200

@server.route('/readiness')
def readiness_check():
    """앱 준비 상태 확인 - Google Sheets 연결 포함"""
    try:
        from data.data import data_manager
        
        # Google Sheets 연결 상태 확인
        sheets_ready = False
        try:
            if data_manager._sheets_manager:
                sheets_ready = data_manager.sheets_manager.is_connected
        except:
            sheets_ready = False
        
        status_code = 200 if sheets_ready else 503
        
        return jsonify({
            'status': 'ready' if sheets_ready else 'initializing',
            'sheets_connected': sheets_ready,
            'service': 'tentlog'
        }), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'service': 'tentlog'
        }), 503

# ===== 위스키 테마 닉네임 생성기 =====
def generate_random_nickname():
    """위스키/바 관련 랜덤 닉네임 생성"""
    surnames = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임', '한', '오', '서', '신', '권', '황', '안', '송', '류', '전']
    
    whiskey_names = [
        '맥캘란', '글렌피딕', '조니워커', '잭다니엘', '짐빔', '발베니',
        '라가불린', '아드벡', '글렌모렌지', '하이볼', '올드패션드',
        '맨하탄', '마티니', '네그로니', '사제락', '민트줄렙', '위스키사워',
        '바텐더', '소믈리에', '마스터', '시나몬', '바닐라', '오크',
        '피트', '스모키', '셰리', '포트', '버번', '라이', '몰트',
        '싱글', '블렌드', '캐스크', '배럴', '스카치', '아이리시',
        '하이랜드', '스페이사이드', '아일레이', '로우랜드', '캠벨타운',
        '디스틸러리', '증류소', '에이징', '숙성', '테이스팅', '노우즈'
    ]
    
    surname = random.choice(surnames)
    name = random.choice(whiskey_names)
    
    return f"{surname}{name}"


# ===== 카카오 OAuth 로그인 엔드포인트 =====

@server.route('/login/kakao')
def login_kakao():
    """1단계: 카카오 인증 페이지로 리다이렉트"""
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_REST_API_KEY}"
        f"&redirect_uri={KAKAO_REDIRECT_URI}"
        f"&response_type=code"
    )
    
    print(f"[카카오 로그인] 인증 페이지로 리다이렉트")
    return redirect(kakao_auth_url)


@server.route('/oauth/kakao/callback')
def oauth_kakao_callback():
    """2단계: 카카오에서 인증 코드를 받아 처리"""
    try:
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error or not code:
            print(f"[카카오 콜백] 인증 실패")
            return redirect('/?error=auth_failed')
        
        # 액세스 토큰 발급
        token_url = "https://kauth.kakao.com/oauth/token"
        token_data = {
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_API_KEY,
            "redirect_uri": KAKAO_REDIRECT_URI,
            "code": code
        }
        
        token_response = requests.post(token_url, data=token_data, timeout=10)
        
        if token_response.status_code != 200:
            print(f"[카카오 콜백] 토큰 발급 실패")
            return redirect('/?error=token_failed')
        
        access_token = token_response.json().get('access_token')
        
        if not access_token:
            return redirect('/?error=no_token')
        
        # 사용자 정보 조회
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        user_response = requests.get(user_info_url, headers=headers, timeout=10)
        
        if user_response.status_code != 200:
            print(f"[카카오 콜백] 사용자 정보 조회 실패")
            return redirect('/?error=user_info_failed')
        
        user_data = user_response.json()
        user_id = user_data.get('id')
        
        if not user_id:
            return redirect('/?error=no_user_id')
        
        kakao_user_id = f"kakao_{user_id}"
        
        # 기존 사용자 확인
        existing_user = get_existing_user(kakao_user_id)
        
        properties = user_data.get('properties', {})
        kakao_account = user_data.get('kakao_account', {})
        
        # 한국 시간
        kst = pytz.timezone('Asia/Seoul')
        current_time = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
        
        # 닉네임 결정
        if existing_user and existing_user.get('nickname'):
            nickname = existing_user['nickname']
        else:
            kakao_nickname = properties.get('nickname')
            nickname = kakao_nickname if kakao_nickname else generate_random_nickname()
        
        # 사용자 데이터 구조
        user_data_dict = {
            "user_id": kakao_user_id,
            "username": nickname,
            "nickname": nickname,
            "email": kakao_account.get("email", ""),
            "login_type": "kakao",
            "created_at": current_time,
            "last_login": current_time
        }
        
        # 세션 저장
        session_data = user_data_dict.copy()
        session_data["profile_image"] = properties.get("profile_image", "")
        session['user_data'] = session_data
        session.permanent = True
        
        # 데이터베이스 저장
        save_kakao_user(user_data_dict)
        
        print(f"[카카오 로그인] 성공: {nickname}")
        
        return redirect('/')
        
    except requests.exceptions.Timeout:
        print(f"[카카오 콜백] 타임아웃")
        return redirect('/?error=timeout')
    except Exception as e:
        print(f"[카카오 콜백] 예외: {str(e)}")
        return redirect('/?error=exception')


@server.route('/api/logout', methods=['POST'])
def logout_endpoint():
    """로그아웃 처리"""
    try:
        session.clear()
        print("[로그아웃] 완료")
        return jsonify({'success': True})
    except Exception as e:
        print(f"[로그아웃] 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@server.route('/api/user-status', methods=['GET'])
def user_status_endpoint():
    """현재 로그인 상태 확인"""
    try:
        user_data = session.get('user_data')
        return jsonify({'logged_in': bool(user_data), 'user': user_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@server.route('/force-logout')
def force_logout():
    """강제 로그아웃 (디버깅용)"""
    session.clear()
    return "로그아웃 완료! <a href='/'>홈으로 이동</a>"


# ===== 유사 리뷰 키워드 저장 (URL 파라미터 방식) =====

@server.before_request
def handle_keyword_save():
    """URL 파라미터로 전달된 키워드 저장 처리"""
    if request.path == '/archive' and request.args.get('save_keyword'):
        try:
            word = request.args.get('save_keyword')
            record_index = request.args.get('record')
            
            print(f"\n{'='*60}")
            print(f"[URL-SAVE] 키워드 저장: {word} (기록 #{record_index})")
            print(f"{'='*60}")
            
            if not word or not record_index:
                return redirect('/archive')
            
            user_data = session.get('user_data')
            if not user_data:
                print(f"[URL-SAVE] ❌ 로그인 필요")
                return redirect('/archive')
            
            from data.data import get_user_records, add_record_keyword
            
            records = get_user_records(user_data['user_id'])
            record_index = int(record_index)
            
            if record_index < 0 or record_index >= len(records):
                print(f"[URL-SAVE] ❌ 기록 인덱스 범위 초과")
                return redirect('/archive')
            
            record = records[record_index]
            record_id = record.get('id') or record.get('timestamp')
            
            # 아카이빙 시트에 저장
            success = add_record_keyword(record_id, user_data['user_id'], word)
            
            if success:
                print(f"[URL-SAVE] ✅ 저장 성공: {record.get('whiskey_name')}")
            else:
                print(f"[URL-SAVE] ❌ 저장 실패")
            
            print(f"{'='*60}\n")
            
            # 파라미터 제거하고 리다이렉트
            return redirect('/archive')
            
        except Exception as e:
            print(f"[URL-SAVE] ❌ 예외: {e}")
            return redirect('/archive')


# 레이아웃 및 콜백 등록
app.layout = get_main_layout
register_callbacks(app)

# ===== HTML 템플릿 =====
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
            <script>
                function connectButtons() {
                    const kakaoBtn = document.getElementById('kakao-login-btn');
                    if (kakaoBtn && !kakaoBtn.hasAttribute('data-connected')) {
                        kakaoBtn.onclick = function(e) { 
                            e.preventDefault(); 
                            window.location.href = '/login/kakao';
                        };
                        kakaoBtn.setAttribute('data-connected', 'true');
                    }
                    
                    const logoutBtn = document.getElementById('logout-btn');
                    if (logoutBtn && !logoutBtn.hasAttribute('data-connected')) {
                        logoutBtn.onclick = function(e) { 
                            e.preventDefault(); 
                            fetch('/api/logout', {method: 'POST'})
                            .then(() => window.location.reload());
                        };
                        logoutBtn.setAttribute('data-connected', 'true');
                    }
                }

                document.addEventListener('DOMContentLoaded', connectButtons);
                setTimeout(connectButtons, 1000);
                setTimeout(connectButtons, 2000);
            </script>
        </footer>
    </body>
</html>
"""
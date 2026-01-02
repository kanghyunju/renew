# components/callbacks.py - 위스키 앱 콜백 (TCC 구조)
import dash
from dash import Input, Output, State, callback, html, dcc, no_update, ALL, MATCH, callback_context
from dash.exceptions import PreventUpdate
from flask import session
import datetime
import traceback
import pytz
import json

from components.layouts import (
    get_home_layout, get_menu_layout, get_search_layout, get_record_layout, 
    get_archive_layout, create_message, _render_records
)


def register_callbacks(app):
    """모든 콜백 함수들을 등록"""
    
    # ===== 페이지 라우팅 =====
    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname"),
        prevent_initial_call=False
    )
    def display_page(pathname):
        """페이지 라우팅 - 데이터 연결"""
        user_data = session.get('user_data')
        
        if pathname == "/" or pathname is None:
            # 메인 페이지 - 빈 레이아웃만 제공 (콜백이 채움)
            return get_home_layout()
            
        elif pathname == "/menu":
            # 메뉴판 페이지
            from data.data import get_hannam_products, get_chungmuro_products
            hannam = get_hannam_products()
            chungmuro = get_chungmuro_products()
            return get_menu_layout(hannam, chungmuro)
            
        elif pathname == "/search":
            # 검색 페이지 (메뉴판과 동일)
            from data.data import get_hannam_products, get_chungmuro_products
            hannam = get_hannam_products()
            chungmuro = get_chungmuro_products()
            return get_search_layout(hannam, chungmuro)
            
        elif pathname == "/record":
            # 기록 페이지
            edit_data = session.get('edit_mode_data')
            selected_whiskey = session.get('selected_whiskey', '')
            
            if edit_data:
                return get_record_layout(edit_data=edit_data)
            else:
                return get_record_layout(selected_whiskey=selected_whiskey)
            
        elif pathname == "/archive":
            # 아카이브 페이지 - 즉시 껍데기 반환 (레이지 로딩)
            if user_data:
                from data.data import get_user_records
                
                # 사용자 이름
                username = user_data.get('nickname') or user_data.get('username') or '사용자'
                
                # 전체 기록 (가벼움)
                records = get_user_records(user_data['user_id'])
                
                # 빈 레이아웃 즉시 반환 (모든 데이터는 콜백으로)
                return get_archive_layout(taste_analysis=None, records=records, username=username)
            from components.layouts import _create_login_required_page
            return _create_login_required_page()
        
        # 404 페이지
        return html.Div([
            html.H2("404 - 페이지를 찾을 수 없습니다", 
                   style={"color": "#FFD700"}),
            dcc.Link("홈으로 돌아가기", href="/", className="btn-primary")
        ], className="card", style={"textAlign": "center", "padding": "40px"})

    
    # ===== 메인 페이지 동적 업데이트 콜백들 =====
    
    @app.callback(
        Output("trend-panel", "children"),
        Input("url", "pathname")
    )
    def update_trend_panel(pathname):
        """현황판 동적 업데이트"""
        if pathname != "/":
            return []
            
        user_data = session.get('user_data')
        if not user_data:
            return []
        
        # 사용자 이름
        username = (
            user_data.get('nickname') or 
            user_data.get('username') or 
            '사용자'
        )
        
        # 최근 트렌드 분석
        from data.data import analyze_recent_taste_trend
        trend_analysis = analyze_recent_taste_trend(user_data['user_id'], n=10)
        
        # 현황판 렌더링
        from components.layouts import _create_trend_panel
        return _create_trend_panel(username, trend_analysis)
    
    
    @app.callback(
        Output("glass-container", "children"),
        Input("url", "pathname")
    )
    def update_glass(pathname):
        """위스키 잔 동적 업데이트 - 모던 디자인"""
        if pathname != "/":
            return []
            
        user_data = session.get('user_data')
        if not user_data:
            return []
        
        from data.data import get_user_records_count
        from components.layouts import _create_whiskey_glass
        
        record_count = get_user_records_count(user_data['user_id'])
        return _create_whiskey_glass(record_count)
    
    
    # ===== 네비게이션 바 동적 업데이트 =====
    @app.callback(
        Output("navbar-container", "children"),
        Input("url", "pathname"),
        prevent_initial_call=False
    )
    def update_navbar(pathname):
        """현재 경로에 따라 네비게이션 바 업데이트"""
        from components.layouts import _get_navbar
        return _get_navbar(pathname or "/")

    
    # ===== 로딩 스피너 콜백들 =====
    @app.callback(
        Output("global-loading", "style"),
        Input("loading-store", "data"),
        prevent_initial_call=True
    )
    def toggle_global_loading_spinner(loading_state):
        """전역 로딩 스피너 표시/숨김 제어"""
        if loading_state:
            return {
                "display": "flex",
                "position": "fixed",
                "top": "0",
                "left": "0",
                "width": "100%",
                "height": "100%",
                "zIndex": "9999",
                "backgroundColor": "rgba(26, 15, 10, 0.85)",
                "backdropFilter": "blur(8px)"
            }
        return {"display": "none"}

    
    # ===== 한남 드롭다운 선택 =====
    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Input("hannam-dropdown", "value"),
        State("chungmuro-dropdown", "value"),
        prevent_initial_call=True
    )
    def handle_hannam_selection(hannam_value, chungmuro_value):
        """한남 드롭다운 선택 - 기록 페이지 이동"""
        if not hannam_value:
            return no_update
        
        # 세션에 저장
        session['selected_whiskey'] = hannam_value
        session['edit_mode_data'] = None
        
        print(f"[한남] 선택: {hannam_value} → /record 이동")
        
        return "/record"

    
    # ===== 충무로 드롭다운 선택 =====
    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Input("chungmuro-dropdown", "value"),
        State("hannam-dropdown", "value"),
        prevent_initial_call=True
    )
    def handle_chungmuro_selection(chungmuro_value, hannam_value):
        """충무로 드롭다운 선택 - 기록 페이지 이동"""
        if not chungmuro_value:
            return no_update
        
        # 세션에 저장
        session['selected_whiskey'] = chungmuro_value
        session['edit_mode_data'] = None
        
        print(f"[충무로] 선택: {chungmuro_value} → /record 이동")
        
        return "/record"

    
    # ===== 기록 저장 콜백 =====
    @app.callback(
        [Output("record-message", "children"),
         Output("loading-store", "data", allow_duplicate=True),
         Output("record-save-btn", "children"),
         Output("record-save-btn", "disabled"),
         Output("record-save-btn", "className"),
         Output("url", "pathname", allow_duplicate=True)],
        Input("record-save-btn", "n_clicks"),
        [State("record-whiskey-name", "value"),
         State("record-taste-notes", "value"),
         State("record-rating", "value"),
         State("record-memo", "value")],
        prevent_initial_call=True
    )
    def save_record_with_loading(n_clicks, whiskey_name, taste_notes, rating, memo):
        """기록 저장 - Google Sheets + 통계 자동 업데이트"""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            print(f"[저장] 기록 저장 시작: {whiskey_name}")
            
            # 유효성 검사
            if not whiskey_name or not whiskey_name.strip():
                return (
                    create_message("warning", "위스키 이름을 입력해주세요"),
                    False,
                    "저장하기",
                    False,
                    "btn-primary btn-large",
                    no_update
                )
            
            if not taste_notes or len(taste_notes) == 0:
                return (
                    create_message("warning", "맛 노트를 최소 1개 이상 선택해주세요"),
                    False,
                    "저장하기",
                    False,
                    "btn-primary btn-large",
                    no_update
                )
            
            if rating is None:
                return (
                    create_message("warning", "별점을 선택해주세요"),
                    False,
                    "저장하기",
                    False,
                    "btn-primary btn-large",
                    no_update
                )
            
            user_data = session.get('user_data')
            if not user_data:
                return (
                    create_message("error", "로그인이 필요합니다"),
                    False,
                    "저장하기",
                    False,
                    "btn-primary btn-large",
                    no_update
                )
            
            # 수정 모드 확인
            edit_mode_data = session.get('edit_mode_data')
            is_edit_mode = edit_mode_data is not None
            
            # 한국 시간
            kst = pytz.timezone('Asia/Seoul')
            now_kst = datetime.datetime.now(kst)
            
            if is_edit_mode:
                # 수정 모드
                print(f"[저장] 수정 모드: {edit_mode_data.get('id')}")
                
                record_data = {
                    "id": edit_mode_data.get('id'),
                    "user_id": user_data['user_id'],
                    "username": user_data.get('username', user_data.get('nickname', '사용자')),
                    "whiskey_name": whiskey_name.strip(),
                    "taste_notes": taste_notes or [],
                    "rating": rating or 3,
                    "memo": memo or "",
                    "timestamp": edit_mode_data.get('timestamp'),
                    "date": edit_mode_data.get('date')
                }
                
            else:
                # 신규 저장
                record_id = now_kst.timestamp()
                
                record_data = {
                    "id": record_id,
                    "user_id": user_data['user_id'],
                    "username": user_data.get('username', user_data.get('nickname', '사용자')),
                    "whiskey_name": whiskey_name.strip(),
                    "taste_notes": taste_notes or [],
                    "rating": rating or 3,
                    "memo": memo or "",
                    "timestamp": now_kst.isoformat(),
                    "date": now_kst.strftime("%Y-%m-%d")
                }
            
            print(f"[저장] 데이터: {record_data}")
            
            # Google Sheets 저장
            save_result = False
            try:
                if is_edit_mode:
                    from data.data import update_whiskey_record
                    save_result = update_whiskey_record(record_data)
                    print(f"[저장] 수정 결과: {save_result}")
                else:
                    from data.data import save_whiskey_record
                    save_result = save_whiskey_record(record_data)
                    print(f"[저장] 저장 결과: {save_result}")
            except ImportError:
                print(f"[저장] data.data 모듈 없음")
                save_result = False
            
            # 세션 정리
            session['selected_whiskey'] = ''
            session['edit_mode_data'] = None
            
            if save_result:
                # users 시트 통계 자동 업데이트
                try:
                    from data.data import update_user_stats
                    stats_updated = update_user_stats(user_data['user_id'])
                    if stats_updated:
                        print(f"[통계] users 시트 통계 업데이트 완료")
                    else:
                        print(f"[통계] users 시트 통계 업데이트 실패")
                except Exception as stats_error:
                    print(f"[통계] 업데이트 실패: {stats_error}")
                
                print(f"[저장] 저장 완료 - 아카이브로 이동")
                success_msg = create_message(
                    "success", 
                    "수정 완료!" if is_edit_mode else "저장 완료!", 
                    f"'{whiskey_name}' 기록이 성공적으로 {'수정' if is_edit_mode else '저장'}되었습니다."
                )
                return (
                    success_msg,
                    False,
                    "완료",
                    True,
                    "btn-primary btn-large",
                    "/archive"
                )
            else:
                error_msg = create_message("error", "저장 실패", "Google Sheets 저장 중 오류가 발생했습니다.")
                return (
                    error_msg,
                    False,
                    "저장하기",
                    False,
                    "btn-primary btn-large",
                    no_update
                )
                
        except Exception as e:
            print(f"[저장] 예외 발생: {str(e)}")
            print(traceback.format_exc())
            
            error_msg = create_message("error", "저장 실패", f"오류가 발생했습니다: {str(e)}")
            return (
                error_msg,
                False,
                "저장하기",
                False,
                "btn-primary btn-large",
                no_update
            )

    
    # ===== 수정 버튼 콜백 =====
    @app.callback(
        [Output("url", "pathname", allow_duplicate=True),
         Output("edit-mode-store", "data")],
        Input({"type": "edit-btn", "index": ALL}, "n_clicks"),
        State({"type": "edit-btn", "index": ALL}, "id"),
        prevent_initial_call=True
    )
    def handle_edit_record(n_clicks_list, button_ids):
        """수정 버튼 클릭 처리"""
        if not any(n_clicks_list):
            raise PreventUpdate
        
        clicked_idx = None
        for i, n_clicks in enumerate(n_clicks_list):
            if n_clicks:
                clicked_idx = button_ids[i]["index"]
                break
        
        if not clicked_idx:
            raise PreventUpdate
        
        print(f"[수정] 수정 요청: {clicked_idx}")
        
        user_data = session.get('user_data')
        if not user_data:
            return no_update, None
        
        from data.data import get_user_records
        records = get_user_records(user_data['user_id'])
        
        if not records:
            print(f"[수정] 사용자 레코드를 찾을 수 없음: {user_data['user_id']}")
            return no_update, None
        
        target_record = None
        for rec in records:
            if str(rec.get('id')) == str(clicked_idx) or str(rec.get('timestamp')) == str(clicked_idx):
                target_record = rec
                break
        
        if not target_record:
            print(f"[수정] 레코드를 찾을 수 없음: {clicked_idx}")
            return no_update, None
        
        session['edit_mode_data'] = target_record
        session['selected_whiskey'] = ''
        print(f"[수정] 수정 모드 활성화: {target_record.get('whiskey_name')}")
        
        return "/record", target_record

    
    # ===== 삭제 버튼 콜백 =====
    @app.callback(
        [Output("archive-records", "children"),
         Output("loading-store", "data", allow_duplicate=True)],
        Input({"type": "delete-btn", "index": ALL}, "n_clicks"),
        State({"type": "delete-btn", "index": ALL}, "id"),
        prevent_initial_call=True
    )
    def handle_delete_record(n_clicks_list, button_ids):
        """삭제 버튼 클릭 처리 + 통계 자동 업데이트"""
        try:
            if not any(n_clicks_list):
                raise PreventUpdate
            
            clicked_idx = None
            for i, n_clicks in enumerate(n_clicks_list):
                if n_clicks:
                    clicked_idx = button_ids[i]["index"]
                    break
            
            if not clicked_idx:
                raise PreventUpdate
            
            print(f"[삭제] 삭제 요청: {clicked_idx}")
            
            user_data = session.get('user_data')
            if not user_data:
                print(f"[삭제] 사용자 정보 없음")
                raise PreventUpdate
            
            from data.data import get_user_records, soft_delete_record
            
            # Soft Delete 실행
            success = soft_delete_record(clicked_idx, user_data['user_id'])
            if success:
                print(f"[삭제] Soft Delete 완료: {clicked_idx}")
            else:
                print(f"[삭제] Soft Delete 실패: {clicked_idx}")
            
            # users 시트 통계 자동 업데이트
            try:
                from data.data import update_user_stats
                stats_updated = update_user_stats(user_data['user_id'])
                if stats_updated:
                    print(f"[통계] users 시트 통계 업데이트 완료")
                else:
                    print(f"[통계] users 시트 통계 업데이트 실패")
            except Exception as stats_error:
                print(f"[통계] 업데이트 실패: {stats_error}")
            
            # 최신 기록 다시 불러오기
            records = get_user_records(user_data['user_id'])
            print(f"[삭제] 갱신된 기록 개수: {len(records)}")
            
            updated_content = _render_records(records)
            
            return updated_content, False
            
        except Exception as e:
            print(f"[삭제] 예외 발생: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise PreventUpdate

    
    # ===== 아카이브 탭 전환 =====
    
    @app.callback(
        [Output("tab-overview", "style"),
         Output("tab-expressions", "style"),
         Output("tab-records", "style"),
         Output("tab-overview-btn", "className"),
         Output("tab-expressions-btn", "className"),
         Output("tab-records-btn", "className")],
        [Input("tab-overview-btn", "n_clicks"),
         Input("tab-expressions-btn", "n_clicks"),
         Input("tab-records-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def switch_archive_tabs(n1, n2, n3):
        """아카이브 탭 전환"""
        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # 기본 스타일
        hidden = {"display": "none"}
        visible = {"display": "block"}
        
        if button_id == "tab-overview-btn":
            return (visible, hidden, hidden, 
                    "archive-tab active", "archive-tab", "archive-tab")
        elif button_id == "tab-expressions-btn":
            return (hidden, visible, hidden,
                    "archive-tab", "archive-tab active", "archive-tab")
        elif button_id == "tab-records-btn":
            return (hidden, hidden, visible,
                    "archive-tab", "archive-tab", "archive-tab active")
        
        return dash.no_update
    
    
    # ===== 기록 목록 탭 로드 =====
    
    @app.callback(
        Output("archive-records", "children", allow_duplicate=True),
        Input("tab-records-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def load_records_tab(n_clicks):
        """기록 목록 탭 클릭 시 로드"""
        if not n_clicks:
            return dash.no_update
        
        user_data = session.get('user_data')
        if not user_data:
            return []
        
        from data.data import get_user_records
        records = get_user_records(user_data['user_id'])
        return _render_records(records)
    
    
    # ===== 유사 리뷰 토글 콜백 =====
    @app.callback(
        Output({"type": "similar-review-content", "index": MATCH}, "children"),
        Output({"type": "similar-review-content", "index": MATCH}, "style"),
        Input({"type": "similar-review-btn", "index": MATCH}, "n_clicks"),
        State({"type": "similar-review-content", "index": MATCH}, "style"),
        State("archive-records", "children"),
        prevent_initial_call=True
    )
    def toggle_similar_review(n_clicks, current_style, records_children):
        """유사 리뷰 워드클라우드 토글"""
        if not n_clicks:
            raise PreventUpdate
        
        user_data = session.get('user_data')
        if not user_data:
            raise PreventUpdate
        
        # 현재 표시 여부 확인
        is_visible = current_style.get("display") != "none" if current_style else False
        
        if is_visible:
            # 숨기기
            return [], {"display": "none", "marginTop": "20px", "paddingTop": "20px",
                       "borderTop": "1px solid rgba(255, 215, 0, 0.1)"}
        else:
            # 보이기 - record_id 가져오기
            ctx = callback_context
            if not ctx.triggered_id:
                raise PreventUpdate
            
            record_id = ctx.triggered_id["index"]
            
            # 해당 기록 찾기
            from data.data import get_user_records, get_product_reviews_wordcloud
            records = get_user_records(user_data['user_id'])
            
            whiskey_name = None
            record_idx = None
            for idx, record in enumerate(records):
                if str(record.get('id', record.get('timestamp', ''))) == str(record_id):
                    whiskey_name = record.get('whiskey_name')
                    record_idx = idx
                    break
            
            if not whiskey_name:
                return html.P("제품명을 찾을 수 없습니다", 
                            style={"color": "rgba(245, 237, 220, 0.5)", "textAlign": "center"}), \
                       {"display": "block", "marginTop": "20px", "paddingTop": "20px",
                        "borderTop": "1px solid rgba(255, 215, 0, 0.1)"}
            
            # 제품별 워드클라우드 가져오기
            result = get_product_reviews_wordcloud(user_data['user_id'], whiskey_name)
            
            if not result['has_data']:
                content = html.P("아직 작성된 유사 리뷰가 없어요", 
                               style={"color": "rgba(245, 237, 220, 0.5)", "textAlign": "center", "padding": "20px"})
            else:
                # 워드클라우드 표시
                from components.layouts import create_similar_review_wordcloud
                
                content = create_similar_review_wordcloud(
                    result['wordcloud'], 
                    result['count'],
                    record_idx
                )
            
            return content, {"display": "block", "marginTop": "20px", "paddingTop": "20px",
                           "borderTop": "1px solid rgba(255, 215, 0, 0.1)"}

    
    # ===== 로그아웃 콜백 =====
    @app.callback(
        [Output("url", "pathname", allow_duplicate=True),
         Output("page-content", "children", allow_duplicate=True)],
        Input("logout-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def handle_logout(n_clicks):
        """로그아웃 처리"""
        if n_clicks:
            session.clear()
            print("[로그아웃] 사용자 로그아웃")
            return "/", get_home_layout()
        raise PreventUpdate

    
    # ===== 페이지 이동 시 초기화 =====
    @app.callback(
        Output("loading-store", "data", allow_duplicate=True),
        Input("url", "pathname"),
        prevent_initial_call=True
    )
    def reset_loading_on_navigation(pathname):
        """페이지 이동 시 로딩 상태 초기화"""
        if pathname != "/record":
            session.pop('edit_mode_data', None)
            session.pop('selected_whiskey', None)
        return False

    
    # ===== 아카이브 노트 카드 콜백 (레이지 로딩) =====
    
    @app.callback(
        Output("main-notes-content", "children"),
        Input("url", "pathname")
    )
    def load_main_notes(pathname):
        """강하게 남은 표현 (레이지 로딩)"""
        if pathname != "/archive":
            return dash.no_update
        
        user_data = session.get('user_data')
        if not user_data:
            return dash.no_update
        
        from data.data import get_user_taste_analysis
        from components.layouts import _create_main_notes_panel
        
        username = user_data.get('nickname') or user_data.get('username') or '사용자'
        taste_analysis = get_user_taste_analysis(user_data['user_id'])
        
        return _create_main_notes_panel(taste_analysis, username)
    
    
    @app.callback(
        Output("sub-notes-content", "children"),
        Input("url", "pathname")
    )
    def load_sub_notes(pathname):
        """약하게 남긴 표현 (레이지 로딩)"""
        if pathname != "/archive":
            return dash.no_update
        
        user_data = session.get('user_data')
        if not user_data:
            return dash.no_update
        
        from data.data import get_user_taste_analysis
        from components.layouts import _create_sub_notes_panel
        
        username = user_data.get('nickname') or user_data.get('username') or '사용자'
        taste_analysis = get_user_taste_analysis(user_data['user_id'])
        
        return _create_sub_notes_panel(taste_analysis, username)
    
    
    # ===== 아카이브 표현 분석 탭 콜백 =====
    
    @app.callback(
        Output("my-wordcloud-content", "children"),
        Input("tab-expressions-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def load_my_wordcloud(n_clicks):
        """내가 자주 쓴 표현"""
        if not n_clicks:
            return dash.no_update
        
        user_data = session.get('user_data')
        if not user_data:
            return html.Div("로그인이 필요합니다", className="card")
        
        try:
            from data.data import get_user_records, _parse_memo_text
            from components.layouts import create_my_wordcloud_card
            
            records = get_user_records(user_data['user_id'])
            all_memos = [r.get('memo', '') for r in records if r.get('memo')]
            word_dict = _parse_memo_text(all_memos)
            
            return create_my_wordcloud_card(word_dict)
        except Exception as e:
            print(f"[ERROR] 내 워드클라우드 로드 실패: {e}")
            return html.Div("워드클라우드를 불러올 수 없습니다", className="card")
    
    
    @app.callback(
        Output("community-wordcloud-content", "children"),
        Input("tab-expressions-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def load_community_wordcloud(n_clicks):
        """커뮤니티 표현 (저장 가능)"""
        if not n_clicks:
            return dash.no_update
        
        user_data = session.get('user_data')
        if not user_data:
            return html.Div("로그인이 필요합니다", className="card")
        
        try:
            from data.data import get_user_taste_analysis, get_similar_users_memo_wordcloud
            from components.layouts import create_community_wordcloud_card
            
            taste_analysis = get_user_taste_analysis(user_data['user_id'])
            
            if not taste_analysis:
                return html.Div([
                    html.Div("Community", className="card-tag"),
                    html.H3("다른 사람들이 자주 쓰는 표현", className="card-title"),
                    html.P("5개 이상 기록하면 표시됩니다", 
                          style={"color": "rgba(245, 237, 220, 0.5)", "textAlign": "center", "padding": "40px"})
                ], className="card")
            
            user_notes = list(taste_analysis.get('main_expressions', {}).keys())
            community_words = get_similar_users_memo_wordcloud(user_data['user_id'], user_notes)
            
            return create_community_wordcloud_card(community_words)
        except Exception as e:
            print(f"[ERROR] 커뮤니티 워드클라우드 로드 실패: {e}")
            return html.Div("워드클라우드를 불러올 수 없습니다", className="card")
    
    
    # ===== 아카이브 워드클라우드 콜백 (스피너 처리) =====
    
    @app.callback(
        Output("wordcloud-content", "children"),
        Input("url", "pathname")
    )
    def update_wordcloud(pathname):
        """다른 사람들이 자주 쓰는 표현 (워드클라우드)"""
        if pathname != "/archive":
            return dash.no_update
        
        user_data = session.get('user_data')
        if not user_data:
            return dash.no_update
        
        from data.data import get_user_taste_analysis, get_similar_users_memo_wordcloud
        from components.layouts import _create_wordcloud_panel
        
        username = user_data.get('nickname') or user_data.get('username') or '사용자'
        taste_analysis = get_user_taste_analysis(user_data['user_id'])
        
        # 유사 사용자 워드클라우드 추가
        if taste_analysis:
            main_notes = list(taste_analysis.get('main_expressions', {}).keys())
            similar_wordcloud = get_similar_users_memo_wordcloud(user_data['user_id'], main_notes)
            taste_analysis['similar_wordcloud'] = similar_wordcloud
        
        return _create_wordcloud_panel(taste_analysis, username)
    
    
    # ===== 워드클라우드 클릭 저장 (통합) =====
    
    # ===== 워드클라우드 클릭 저장 (아카이브만) =====
    
    @app.callback(
        Output("saved-expressions-display", "children"),
        Input({"type": "wordcloud-word", "word": ALL}, "n_clicks"),
        State({"type": "wordcloud-word", "word": ALL}, "id"),
        prevent_initial_call=False
    )
    def handle_archive_wordcloud_clicks(n_clicks_list, button_ids):
        """아카이브 워드클라우드 클릭 처리 (내 표현 + 커뮤니티)"""
        print(f"\n{'='*60}")
        print(f"[KEYWORD-ARCHIVE] 아카이브 워드클라우드 클릭")
        print(f"{'='*60}")
        print(f"[KEYWORD-ARCHIVE] n_clicks: {n_clicks_list}")
        
        if not n_clicks_list or not any(n_clicks_list):
            print(f"[KEYWORD-ARCHIVE] 초기 로드")
            return dash.no_update
        
        user_data = session.get('user_data')
        if not user_data:
            print(f"[KEYWORD-ARCHIVE] ❌ 사용자 없음")
            return dash.no_update
        
        ctx = dash.callback_context
        if not ctx.triggered:
            print(f"[KEYWORD-ARCHIVE] ❌ triggered 없음")
            return dash.no_update
        
        try:
            import json
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
            button_id = json.loads(triggered_id)
            clicked_word = button_id['word']
            record_index = button_id.get('record')
            
            print(f"[KEYWORD-ARCHIVE] 🎯 단어: '{clicked_word}', record: {record_index}")
            
            # 아카이브만 처리 (record 없음)
            if record_index is None:
                print(f"[KEYWORD-ARCHIVE] 📝 Users 시트 저장")
                from data.data import add_preferred_keyword, get_user_preferred_keywords
                
                success = add_preferred_keyword(user_data['user_id'], clicked_word)
                print(f"[KEYWORD-ARCHIVE] 💾 결과: {success}")
                
                if success:
                    keywords = get_user_preferred_keywords(user_data['user_id'])
                    print(f"[KEYWORD-ARCHIVE] ✅ 성공! 키워드: {keywords}")
                    
                    return html.Div([
                        html.Div("저장한 표현 (전반적 선호)", style={
                            "fontSize": "12px", "color": "rgba(255, 215, 0, 0.7)",
                            "marginBottom": "8px", "fontWeight": "600"
                        }),
                        html.Div([
                            html.Span(kw, style={
                                "display": "inline-block", "padding": "4px 10px",
                                "margin": "3px", "background": "rgba(255, 215, 0, 0.1)",
                                "border": "1px solid rgba(255, 215, 0, 0.25)",
                                "borderRadius": "15px", "fontSize": "12px", "color": "#FFD700"
                            }) for kw in keywords
                        ], style={"display": "flex", "flexWrap": "wrap", "gap": "4px"})
                    ], style={"marginTop": "12px", "padding": "12px",
                             "background": "rgba(255, 215, 0, 0.03)", "borderRadius": "8px"})
            else:
                print(f"[KEYWORD-ARCHIVE] ⚠️ 유사 리뷰 버튼 (무시)")
                return dash.no_update
            
            return dash.no_update
            
        except Exception as e:
            print(f"[ERROR] 아카이브 클릭 실패: {e}")
            import traceback
            traceback.print_exc()
            return dash.no_update
    


print("[콜백] 모든 콜백 등록 완료 (TCC 구조 + 탭 전환 + 워드클라우드)")
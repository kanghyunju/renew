# components/layouts.py - tentlog 위스키 기록장 레이아웃 (TCC 구조)
from dash import html, dcc
from flask import session
from typing import Dict, List, Optional


def get_main_layout():
    """메인 레이아웃 - 모든 페이지의 컨테이너"""
    return html.Div([
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="loading-store", data=False),
        dcc.Store(id="edit-mode-store", data=None),
        dcc.Store(id="current-path-store", data="/"),
        
        # 전역 로딩 스피너 (완전히 독립)
        html.Div([
            html.Div([
                html.Div(className="spinner"),
                html.P("처리 중...", style={
                    "color": "#FFD700",
                    "marginTop": "20px",
                    "fontSize": "18px",
                    "textAlign": "center"
                })
            ], style={
                "position": "absolute",
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%)",
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "center",
                "justifyContent": "center"
            })
        ], id="global-loading", style={
            "display": "none"
        }),
        
        # 네비게이션 바 (동적으로 업데이트됨)
        html.Div(id="navbar-container"),
        
        # 페이지 콘텐츠
        html.Div(id="page-content", style={"paddingTop": "100px"})  # 80px → 100px
    ])


def _get_navbar(current_path="/"):
    """네비게이션 바 - 행동 진입점"""
    user_data = session.get('user_data')
    
    if user_data:
        # 로그인 상태: 홈/기록/아카이브/로그아웃
        right_content = html.Div([
            dcc.Link("홈", href="/", className="btn-secondary btn-small",
                    style={"textDecoration": "none", "marginRight": "8px", "padding": "8px 16px"}),
            dcc.Link("기록", href="/menu", className="btn-secondary btn-small",
                    style={"textDecoration": "none", "marginRight": "8px", "padding": "8px 16px"}),
            dcc.Link("아카이브", href="/archive", className="btn-secondary btn-small",
                    style={"textDecoration": "none", "marginRight": "8px", "padding": "8px 16px"}),
            html.Button(
                "로그아웃",
                id="logout-btn", 
                className="btn-logout btn-small",
                style={"cursor": "pointer", "padding": "8px 16px"}
            )
        ], style={"display": "flex", "alignItems": "center"})
    else:
        # 비로그인 상태: 아무것도 표시 안 함
        right_content = html.Div()
    
    return html.Nav([
        html.Div([
            dcc.Link([
                html.Span(className="logo-icon"),
                html.Span("tentlog", className="logo-text")
            ], href="/", className="nav-brand", style={"display": "flex", "alignItems": "center", "gap": "12px", "textDecoration": "none"}),
            html.Div([
                right_content
            ], className="nav-links")
        ], className="nav-container")
    ], className="navbar")


def _create_trend_panel(username, trend_analysis):
    """현황판 - 원래 문구"""
    if not trend_analysis:
        return html.Div([
            html.P(f"{username}님, 환영합니다!", 
                  style={"fontSize": "18px", "color": "#FFFFFF", "marginBottom": "8px", "fontWeight": "700"}),
            html.P("5개 이상 기록하면 취향 분석이 시작됩니다", 
                  style={"color": "rgba(245, 237, 220, 0.6)", "fontSize": "15px"})
        ], className="card", style={"textAlign": "center", "padding": "32px"})
    
    if trend_analysis.get('is_clear_trend'):
        top_note_kr = trend_analysis.get('top_note_korean', '')
        return html.Div([
            html.P(f"{username}님은", 
                  style={"fontSize": "16px", "color": "#FFFFFF", "marginBottom": "6px", "fontWeight": "700"}),
            html.P("최근 기록에서", 
                  style={"fontSize": "16px", "color": "rgba(245, 237, 220, 0.75)", "marginBottom": "6px"}),
            html.P(f"{top_note_kr} 계열 표현을 자주 사용했어요", 
                  style={"fontSize": "20px", "color": "#FFD700", "fontWeight": "600", "lineHeight": "1.4"})
        ], className="card", style={"textAlign": "center", "padding": "32px"})
    else:
        return html.Div([
            html.P(f"{username}님은", 
                  style={"fontSize": "16px", "color": "#FFFFFF", "marginBottom": "6px", "fontWeight": "700"}),
            html.P("최근 기록에서", 
                  style={"fontSize": "16px", "color": "rgba(245, 237, 220, 0.75)", "marginBottom": "6px"}),
            html.P("여러 노트가 고르게 등장해요", 
                  style={"fontSize": "20px", "color": "rgba(245, 237, 220, 0.9)", "fontWeight": "600", "lineHeight": "1.4"})
        ], className="card", style={"textAlign": "center", "padding": "32px"})


def get_home_layout(trend_analysis=None, record_count=0):
    """
    메인 페이지 - 모던 디자인
    """
    user_data = session.get('user_data')
    
    # 비로그인 상태
    if not user_data:
        return html.Div([
            html.Div([
                # 위스키 잔 로고
                html.Div(className="logo-icon", style={"width": "60px", "height": "75px", "margin": "0 auto 32px"}),
                html.H1("tentlog", style={"fontSize": "48px", "marginBottom": "16px", "fontFamily": "Syne, sans-serif", "fontWeight": "700"}),
                html.P("위스키 취향 기록장", style={"color": "var(--text-gray)", "fontSize": "18px", "marginBottom": "48px"}),
                html.Button(
                    "카카오 로그인",
                    id="kakao-login-btn",
                    className="btn-primary btn-large"
                )
            ], style={"textAlign": "center", "padding": "80px 20px"})
        ], style={"padding": "40px 20px", "maxWidth": "500px", "margin": "0 auto"})
    
    # 로그인 상태
    return html.Div([
        # 현황판 (콜백에서 채움)
        html.Div(id="trend-panel", style={"marginBottom": "60px"}),
        
        # 액션 카드 그리드
        html.Div([
            # 기록하기 카드
            html.Div([
                html.Div("Action", className="card-tag"),
                html.H2("기록하기", style={"fontSize": "28px", "fontFamily": "Syne, sans-serif", "marginBottom": "16px"}),
                html.P("새로운 위스키를 기록하세요", style={"color": "var(--text-gray)", "marginBottom": "32px"}),
                dcc.Link("시작하기", href="/menu", className="btn-primary")
            ], className="card"),
            
            # 위스키 잔 (콜백에서 채움)
            html.Div(id="glass-container", className="card")
        ], className="grid", style={"marginBottom": "60px"})
        
    ], style={"maxWidth": "1400px", "margin": "0 auto", "padding": "60px 40px"})


def whiskey_glass_visual(fill_ratio):
    """
    CSS로 위스키 잔 구현
    fill_ratio: 0.0 ~ 1.0
    """
    fill_percentage = fill_ratio * 100
    
    return html.Div([
        html.Div(
            className="glass-liquid",
            style={"height": f"{fill_percentage}%"}
        )
    ], className="glass-container")


def _create_whiskey_glass(record_count):
    """위스키 잔 - 모던 스타일 + 3D 애니메이션"""
    current_fill = record_count % 10
    fill_percentage = (current_fill / 10) * 65 if current_fill > 0 else 0
    completed_glasses = record_count // 10
    
    return html.Div([
        html.Div("Progress", className="card-tag"),
        html.H2(f"{record_count}개 기록", style={"fontSize": "28px", "fontFamily": "Syne, sans-serif", "marginBottom": "16px"}),
        html.P(
            f"{10 - current_fill}개 더 기록하면 {completed_glasses + 1}잔 완성" if current_fill < 10 else f"{completed_glasses}잔 완성!",
            style={"color": "var(--text-gray)", "marginBottom": "32px"}
        ),
        
        # 3D 위스키 잔 (실제로 채워짐)
        html.Div([
            html.Div([
                html.Div(
                    className="glass-liquid",
                    style={"height": f"{fill_percentage}%"}  # ← 여기서 채워짐!
                )
            ], className="glass-shape")
        ], className="glass-visual")
    ])


def get_menu_layout(hannam_products=None, chungmuro_products=None):
    """메뉴판 페이지 - 모던 스타일"""
    
    hannam_options = []
    if hannam_products:
        hannam_options = [{"label": name, "value": name} for name in hannam_products]
    
    chungmuro_options = []
    if chungmuro_products:
        chungmuro_options = [{"label": name, "value": name} for name in chungmuro_products]
    
    return html.Div([
        # 헤더
        html.Div([
            html.H1("메뉴판", style={"fontFamily": "Syne, sans-serif"}),
            html.P("한남 또는 충무로 지점의 위스키를 선택하세요", style={"color": "var(--text-gray)", "fontSize": "18px"})
        ], style={"marginBottom": "60px"}),
        
        # 그리드
        html.Div([
            # 한남 카드
            html.Div([
                html.Div("Hannam", className="card-tag"),
                html.H2("한남", className="card-title", style={"fontSize": "28px", "marginBottom": "24px"}),
                dcc.Dropdown(
                    id="hannam-dropdown",
                    options=hannam_options,
                    placeholder="위스키 이름을 검색해보세요",
                    searchable=True,
                    clearable=True,
                    className="custom-dropdown"
                ),
            ], className="card", style={"marginBottom": "120px"}),
            
            # 충무로 카드
            html.Div([
                html.Div("Chungmuro", className="card-tag"),
                html.H2("충무로", className="card-title", style={"fontSize": "28px", "marginBottom": "24px"}),
                dcc.Dropdown(
                    id="chungmuro-dropdown",
                    options=chungmuro_options,
                    placeholder="위스키 이름을 검색해보세요",
                    searchable=True,
                    clearable=True,
                    style={"fontSize": "15px"},
                    className="custom-dropdown"
                ),
            ], className="card", style={"marginBottom": "120px"}),
        ]),
        
        # 직접 입력
        html.Div([
            dcc.Link(
                "직접 입력하기",
                href="/record",
                className="btn-secondary btn-large",
                style={"width": "100%", "marginTop": "20px", "display": "block", "textAlign": "center", "textDecoration": "none"}
            )
        ]),
        
    ], style={"maxWidth": "600px", "margin": "0 auto", "padding": "20px"})


def get_search_layout(hannam_products=None, chungmuro_products=None):
    """검색 페이지 - 기존 기능 유지"""
    return get_menu_layout(hannam_products, chungmuro_products)


def get_record_layout(selected_whiskey="", edit_data=None):
    """기록 페이지"""
    user_data = session.get('user_data')
    
    if not user_data:
        return _create_login_required_page()
    
    is_edit_mode = edit_data is not None
    
    if is_edit_mode:
        whiskey_name_value = edit_data.get('whiskey_name', '')
        taste_notes_value = edit_data.get('taste_notes', [])
        rating_value = edit_data.get('rating', 3)
        memo_value = edit_data.get('memo', '')
        page_title = "기록 수정"
        page_subtitle = f"'{whiskey_name_value}' 기록을 수정합니다"
    else:
        whiskey_name_value = selected_whiskey
        taste_notes_value = []
        rating_value = 3
        memo_value = ""
        page_title = "테이스팅 기록"
        page_subtitle = "위스키의 향과 맛을 기록하세요"
    
    # 맛 노트 옵션 (이모지 제거)
    taste_options = [
        {"label": "프루티", "value": "fruity"},
        {"label": "플로럴", "value": "floral"},
        {"label": "스윗", "value": "sweet"},
        {"label": "우디", "value": "oaky"},
        {"label": "너티", "value": "nutty"},
        {"label": "피트", "value": "peaty"},
        {"label": "스모키", "value": "smoky"},
        {"label": "스파이시", "value": "spicy"},
    ]
    
    return html.Div([
        html.Div([
            html.H1(page_title, 
                   style={"marginBottom": "8px", "color": "#FFD700"}),
            html.P(page_subtitle, 
                  style={"color": "#FFECB3", "marginBottom": "0"}),
        ], style={"textAlign": "center", "marginBottom": "30px"}),
        
        html.Div([
            html.Div(id="record-message"),
            
            # 위스키 이름
            html.Div([
                html.Label("위스키 이름", className="form-label"),
                dcc.Input(
                    id="record-whiskey-name",
                    type="text",
                    placeholder="예: 글렌피딕 12년",
                    value=whiskey_name_value,
                    className="form-input",
                    disabled=is_edit_mode
                )
            ], style={"marginBottom": "24px"}),
            
            # 맛 노트
            html.Div([
                html.Label("노트 (복수 선택 가능)", className="form-label"),
                dcc.Checklist(
                    id="record-taste-notes",
                    options=taste_options,
                    value=taste_notes_value,
                    className="taste-checklist",
                    labelStyle={"display": "block", "marginBottom": "12px"}
                )
            ], style={"marginBottom": "24px"}),
            
            # 별점
            html.Div([
                html.Label("별점", className="form-label"),
                dcc.RadioItems(
                    id="record-rating",
                    options=[
                        {"label": "⭐", "value": 1},
                        {"label": "⭐⭐", "value": 2},
                        {"label": "⭐⭐⭐", "value": 3},
                        {"label": "⭐⭐⭐⭐", "value": 4},
                        {"label": "⭐⭐⭐⭐⭐", "value": 5},
                    ],
                    value=rating_value,
                    className="rating-radio",
                    labelStyle={"display": "inline-block", "marginRight": "16px"}
                )
            ], style={"marginBottom": "24px"}),
            
            # 메모
            html.Div([
                html.Label("메모 (선택사항)", className="form-label"),
                dcc.Textarea(
                    id="record-memo",
                    placeholder="자유롭게 기록하세요...",
                    value=memo_value,
                    className="form-textarea"
                )
            ], style={"marginBottom": "32px"}),
            
            # 저장 버튼
            html.Button(
                "저장하기",
                id="record-save-btn",
                className="btn-primary btn-large",
                style={"width": "100%"}
            )
            
        ], className="card")
        
    ], style={"maxWidth": "600px", "margin": "0 auto", "padding": "20px"})


def get_archive_layout(taste_analysis=None, records=None, username="사용자"):
    """
    아카이브 페이지 - 탭 구조로 재설계
    """
    user_data = session.get('user_data')
    
    if not user_data:
        return _create_login_required_page()
    
    return html.Div([
        # 헤더
        html.Div([
            html.H1("나의 아카이브", style={"fontFamily": "Syne, sans-serif", "fontSize": "36px", "marginBottom": "8px", "color": "#FFD700"}),
            html.P(f"총 {len(records) if records else 0}개의 기록", style={"color": "rgba(245, 237, 220, 0.6)", "fontSize": "15px"})
        ], style={"marginBottom": "50px"}),
        
        # 탭 네비게이션
        html.Div([
            html.Button("Overview", id="tab-overview-btn", className="archive-tab active"),
            html.Button("표현 분석", id="tab-expressions-btn", className="archive-tab"),
            html.Button("기록 목록", id="tab-records-btn", className="archive-tab"),
        ], className="archive-tabs", style={
            "display": "flex",
            "gap": "12px",
            "marginBottom": "40px",
            "borderBottom": "1px solid rgba(255, 215, 0, 0.1)",
            "paddingBottom": "0"
        }),
        
        # Overview 탭
        html.Div([
            # 통계 3개
            html.Div([
                html.Div([
                    html.Div(str(len(records) if records else 0), style={"fontSize": "32px", "fontWeight": "700", "color": "#FFD700", "fontFamily": "Syne, sans-serif", "marginBottom": "6px"}),
                    html.Div("Total Records", style={"fontSize": "13px", "color": "rgba(245, 237, 220, 0.5)", "textTransform": "uppercase", "letterSpacing": "0.5px"})
                ], style={"background": "rgba(26, 15, 10, 0.4)", "border": "1px solid rgba(255, 215, 0, 0.08)", "borderRadius": "12px", "padding": "20px", "textAlign": "center"}),
                html.Div([
                    html.Div("8", style={"fontSize": "32px", "fontWeight": "700", "color": "#FFD700", "fontFamily": "Syne, sans-serif", "marginBottom": "6px"}),
                    html.Div("Taste Notes", style={"fontSize": "13px", "color": "rgba(245, 237, 220, 0.5)", "textTransform": "uppercase", "letterSpacing": "0.5px"})
                ], style={"background": "rgba(26, 15, 10, 0.4)", "border": "1px solid rgba(255, 215, 0, 0.08)", "borderRadius": "12px", "padding": "20px", "textAlign": "center"}),
                html.Div([
                    html.Div("4.2", style={"fontSize": "32px", "fontWeight": "700", "color": "#FFD700", "fontFamily": "Syne, sans-serif", "marginBottom": "6px"}),
                    html.Div("Avg Rating", style={"fontSize": "13px", "color": "rgba(245, 237, 220, 0.5)", "textTransform": "uppercase", "letterSpacing": "0.5px"})
                ], style={"background": "rgba(26, 15, 10, 0.4)", "border": "1px solid rgba(255, 215, 0, 0.08)", "borderRadius": "12px", "padding": "20px", "textAlign": "center"}),
            ], style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(200px, 1fr))", "gap": "16px", "marginBottom": "40px"}),
            
            # 표현 카드 2개
            html.Div([
                html.Div(id="main-notes-content"),
                html.Div(id="sub-notes-content"),
            ], style={"display": "grid", "gridTemplateColumns": "repeat(2, 1fr)", "gap": "24px"}),
        ], id="tab-overview", className="tab-content active"),
        
        # 표현 분석 탭
        html.Div([
            # 내 표현 (읽기 전용)
            html.Div(id="my-wordcloud-content"),
            # 커뮤니티 표현 (저장 가능)
            html.Div(id="community-wordcloud-content"),
            # 저장된 표현
            html.Div(id="saved-expressions-display", style={"marginTop": "24px"})
        ], id="tab-expressions", className="tab-content", style={"display": "none"}),
        
        # 기록 목록 탭
        html.Div([
            html.Div(id="archive-records")
        ], id="tab-records", className="tab-content", style={"display": "none"}),
        
        # 설문 버튼
        _create_survey_button(),
        
    ], style={"maxWidth": "1200px", "margin": "0 auto", "padding": "40px 20px"})


def _create_wordcloud_display(word_counts: Dict[str, int], max_words: int = 20, record_index: int = None):
    """
    워드클라우드 단순 표시 (빈도순 상위 N개) - 클릭 가능
    
    Args:
        word_counts: {단어: 빈도}
        max_words: 최대 표시 단어 수
        record_index: 기록 인덱스 (유사 리뷰용)
    """
    if not word_counts:
        return html.Div([
            html.P("아직 충분한 데이터가 없습니다", 
                  style={"textAlign": "center", "color": "rgba(245, 237, 220, 0.5)", "padding": "20px"})
        ])
    
    # 빈도순 정렬
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:max_words]
    
    # 최대값으로 정규화
    max_count = sorted_words[0][1] if sorted_words else 1
    
    word_items = []
    for word, count in sorted_words:
        # 크기 계산 (12px ~ 28px)
        size = 12 + int((count / max_count) * 16)
        
        # ID 생성
        button_id = {"type": "wordcloud-word", "word": word}
        
        # 유사 리뷰용 - 링크로 변경
        if record_index is not None:
            button_id["record"] = str(record_index)
            # URL 파라미터 방식
            save_url = f"/archive?save_keyword={word}&record={record_index}"
            
            word_items.append(
                html.A(
                    word,
                    href=save_url,
                    className="wordcloud-word-btn similar-review-word",
                    style={
                        "display": "inline-block",
                        "padding": "6px 12px",
                        "margin": "4px",
                        "fontSize": f"{size}px",
                        "color": f"rgba(245, 237, 220, {0.5 + (count / max_count) * 0.5})",
                        "fontWeight": "500",
                        "background": "transparent",
                        "border": "none",
                        "cursor": "pointer",
                        "transition": "all 0.2s ease",
                        "textDecoration": "none"
                    }
                )
            )
        else:
            # 아카이브용 - 기존 버튼
            word_items.append(
                html.Button(
                    word,
                    id=button_id,
                    className="wordcloud-word-btn",
                    style={
                        "display": "inline-block",
                        "padding": "6px 12px",
                        "margin": "4px",
                        "fontSize": f"{size}px",
                        "color": f"rgba(245, 237, 220, {0.5 + (count / max_count) * 0.5})",
                        "fontWeight": "500",
                        "background": "transparent",
                        "border": "none",
                        "cursor": "pointer",
                        "transition": "all 0.2s ease"
                    }
                )
            )
    
    return html.Div(word_items, style={"textAlign": "center", "padding": "20px", "lineHeight": "2"})



def create_my_wordcloud_card(word_counts: Dict[str, int]):
    """내가 자주 쓴 표현 카드"""
    if not word_counts:
        return html.Div([
            html.Div("My", className="card-tag"),
            html.H3("내가 자주 쓴 표현", className="card-title"),
            html.P("5개 이상 기록하면 표시됩니다", 
                  style={"color": "rgba(245, 237, 220, 0.5)", "textAlign": "center", "padding": "40px"})
        ], className="card")
    
    return html.Div([
        html.Div("My", className="card-tag"),
        html.H3("내가 자주 쓴 표현", className="card-title"),
        html.P("내 메모에서 자주 사용한 표현이에요", 
              style={"color": "rgba(245, 237, 220, 0.6)", "marginBottom": "20px"}),
        _create_wordcloud_display(word_counts, max_words=20)
    ], className="card")


def create_community_wordcloud_card(word_counts: Dict[str, int]):
    """커뮤니티 워드클라우드 카드"""
    if not word_counts:
        return html.Div([
            html.Div("Community", className="card-tag"),
            html.H3("다른 사람들이 자주 쓰는 표현", className="card-title"),
            html.P("아직 충분한 데이터가 없습니다", 
                  style={"color": "rgba(245, 237, 220, 0.5)", "textAlign": "center", "padding": "40px"})
        ], className="card")
    
    return html.Div([
        html.Div("Community", className="card-tag"),
        html.H3("다른 사람들이 자주 쓰는 표현", className="card-title"),
        html.P("같은 노트를 좋아하는 사람들의 표현이에요", 
              style={"color": "rgba(245, 237, 220, 0.6)", "marginBottom": "20px"}),
        _create_wordcloud_display(word_counts, max_words=20)
    ], className="card")


def create_similar_review_wordcloud(wordcloud_data: Dict[str, int], count: int, record_index: int):
    """유사 리뷰 워드클라우드 컨테이너 생성"""
    return html.Div([
        html.P(f"다른 사람들의 표현 ({count}개 리뷰)", 
              style={"color": "rgba(245, 237, 220, 0.75)", "fontSize": "14px", 
                     "marginBottom": "8px", "textAlign": "center"}),
        html.P([
            html.Span("마음에 드는 표현을 클릭", style={"color": "#E6AF2E"}),
            "해서 저장하세요"
        ], style={"fontSize": "13px", "color": "rgba(245, 237, 220, 0.6)", 
                 "marginBottom": "16px", "textAlign": "center"}),
        _create_wordcloud_display(wordcloud_data, max_words=15, record_index=record_index)
    ])




def _create_main_notes_panel(taste_analysis, username="사용자"):
    """강하게 남은 표현 - 모던 스타일"""
    if not taste_analysis:
        return html.Div([
            html.Div("주요 표현", className="card-tag"),
            html.H2("강하게 남은 표현", className="card-title"),
            html.P("5개 이상 기록하면 분석이 시작됩니다", className="card-desc")
        ], className="card")
    
    main_expressions = taste_analysis.get('main_expressions', {})
    
    if not main_expressions:
        return html.Div([
            html.Div("주요 표현", className="card-tag"),
            html.H2("강하게 남은 표현", className="card-title"),
            html.P("★★★★ 이상 기록이 쌓이면 중심 표현을 확인할 수 있습니다", className="card-desc")
        ], className="card")
    
    # 영문 → 한글
    note_mapping = {
        "fruity": "프루티", "floral": "플로럴", "sweet": "스윗", "oaky": "우디",
        "nutty": "너티", "peaty": "피트", "smoky": "스모키", "spicy": "스파이시"
    }
    
    # 상위 노트들
    sorted_notes = sorted(main_expressions.items(), key=lambda x: x[1], reverse=True)
    note_names_kr = [note_mapping.get(note, note) for note, _ in sorted_notes]
    
    # 문장 생성
    if len(note_names_kr) >= 2:
        note_text = f"{note_names_kr[0]}하고 {note_names_kr[1]}한 표현"
    else:
        note_text = f"{note_names_kr[0]}한 표현"
    
    sentence = f"{note_text}을 가장 많이 기록했습니다"
    
    # 태그 생성
    tags = [html.Span(name, className="tag") for name in note_names_kr[:4]]
    
    return html.Div([
        html.Div("주요 표현", className="card-tag"),
        html.H2("강하게 남은 표현", className="card-title"),
        html.P(sentence, className="card-desc"),
        html.Div(tags, className="tags")
    ], className="card")


def _create_sub_notes_panel(taste_analysis, username="사용자"):
    """약하게 남긴 표현 - 모던 스타일"""
    if not taste_analysis:
        return html.Div([
            html.Div("보조 표현", className="card-tag"),
            html.H2("약하게 남긴 표현", className="card-title"),
            html.P("5개 이상 기록하면 분석이 시작됩니다", className="card-desc")
        ], className="card")
    
    sub_expressions = taste_analysis.get('sub_expressions', {})
    
    if not sub_expressions:
        return html.Div([
            html.Div("보조 표현", className="card-tag"),
            html.H2("약하게 남긴 표현", className="card-title"),
            html.P("기록이 쌓이면 주변 표현을 확인할 수 있습니다", className="card-desc")
        ], className="card")
    
    # 영문 → 한글
    note_mapping = {
        "fruity": "프루티", "floral": "플로럴", "sweet": "스윗", "oaky": "우디",
        "nutty": "너티", "peaty": "피트", "smoky": "스모키", "spicy": "스파이시"
    }
    
    # 상위 노트들
    sorted_notes = sorted(sub_expressions.items(), key=lambda x: x[1], reverse=True)
    note_names_kr = [note_mapping.get(note, note) for note, _ in sorted_notes]
    
    # 문장 생성
    if len(note_names_kr) >= 2:
        note_text = f"{note_names_kr[0]}, {note_names_kr[1]}한 표현"
    else:
        note_text = f"{note_names_kr[0]}한 표현"
    
    sentence = f"{note_text}도 가끔 경험했습니다"
    
    # 태그 생성
    tags = [html.Span(name, className="tag") for name in note_names_kr[:3]]
    
    return html.Div([
        html.Div("보조 표현", className="card-tag"),
        html.H2("약하게 남긴 표현", className="card-title"),
        html.P(sentence, className="card-desc"),
        html.Div(tags, className="tags")
    ], className="card")


def _create_wordcloud_panel(taste_analysis, username="사용자"):
    """다른 사람들이 자주 쓰는 표현 - 모던 스타일 + 3D 위스키 잔"""
    if not taste_analysis:
        return html.Div([
            html.Div("Community Insights", className="card-tag"),
            html.H2("다른 사람들이 자주 쓰는 표현", className="card-title"),
            html.P("5개 이상 기록하면 분석이 시작됩니다", className="card-desc")
        ], className="card")
    
    similar_wordcloud = taste_analysis.get('similar_wordcloud', {})
    
    if not similar_wordcloud:
        return html.Div([
            # 3D 위스키 잔
            html.Div([
                html.Div([
                    html.Div(className="glass-liquid")
                ], className="glass-shape")
            ], className="glass-visual"),
            html.Div("Community Insights", className="card-tag"),
            html.H2("다른 사람들이 자주 쓰는 표현", className="card-title"),
            html.P("같은 노트를 기록한 사용자가 아직 없습니다", className="card-desc")
        ], className="card")
    
    # 상위 단어들
    sorted_words = sorted(similar_wordcloud.items(), key=lambda x: x[1], reverse=True)[:9]
    
    # 상위 2-3개로 문장 생성
    if len(sorted_words) >= 2:
        word_text = f"{sorted_words[0][0]}, {sorted_words[1][0]}"
    else:
        word_text = f"{sorted_words[0][0]}"
    
    sentence = f"같은 노트를 기록한 사람들은 이런 표현을 사용했습니다"
    
    # 크기별 태그 생성
    max_count = sorted_words[0][1] if sorted_words else 1
    tags = []
    
    for word, count in sorted_words:
        # 크기 계산 (14px ~ 20px)
        size = 14 + int((count / max_count) * 6)
        padding_v = 10 + int((count / max_count) * 4)
        padding_h = 20 + int((count / max_count) * 8)
        
        tags.append(
            html.Span(
                word,
                className="tag",
                style={"fontSize": f"{size}px", "padding": f"{padding_v}px {padding_h}px"}
            )
        )
    
    return html.Div([
        # 3D 위스키 잔
        html.Div([
            html.Div([
                html.Div(className="glass-liquid")
            ], className="glass-shape")
        ], className="glass-visual"),
        html.Div("Community Insights", className="card-tag"),
        html.H2("다른 사람들이 자주 쓰는 표현", className="card-title"),
        html.P(sentence, className="card-desc", style={"marginBottom": "30px"}),
        html.Div(tags, className="tags")
    ], className="card")


def _create_my_expression_panel(taste_analysis, username="사용자"):
    """타인 기록·중심 - 문장 + 워드클라우드"""
    if not taste_analysis:
        return html.Div([
            html.Div("다른 사람들이 자주 쓰는 표현", className="card-header"),
            html.P("5개 이상 기록하면 분석이 시작됩니다", 
                  style={"textAlign": "center", "color": "rgba(245, 237, 220, 0.5)", "padding": "60px 20px", "fontSize": "14px"})
        ], className="card")
    
    similar_wordcloud = taste_analysis.get('similar_wordcloud', {})
    
    if not similar_wordcloud:
        sentence = "같은 노트를 기록한 사용자가 아직 없습니다."
    else:
        # 상위 2-3개 단어 추출
        sorted_words = sorted(similar_wordcloud.items(), key=lambda x: x[1], reverse=True)[:3]
        word_names = [word for word, _ in sorted_words]
        
        if len(word_names) >= 2:
            word_text = f"{word_names[0]}, {word_names[1]}"
        else:
            word_text = f"{word_names[0]}"
        
        sentence = f"같은 노트를 기록한 사람들은 {word_text} 같은 표현을 자주 사용했습니다."
    
    return html.Div([
        html.Div("다른 사람들이 자주 쓰는 표현", className="card-header"),
        html.P(sentence, style={
            "color": "rgba(245, 237, 220, 0.75)",
            "fontSize": "15px",
            "lineHeight": "1.7",
            "padding": "32px 24px 16px 24px",
            "textAlign": "center"
        }),
        _create_wordcloud_display(similar_wordcloud, max_words=12) if similar_wordcloud else None
    ], className="card")


def _create_similar_memo_panel(taste_analysis, username="사용자"):
    """타인 기록·주변 - 문장 + 워드클라우드"""
    if not taste_analysis:
        return html.Div([
            html.Div("다른 사람에게서 스쳐간 표현", className="card-header"),
            html.P("5개 이상 기록하면 분석이 시작됩니다", 
                  style={"textAlign": "center", "color": "rgba(245, 237, 220, 0.5)", "padding": "60px 20px", "fontSize": "14px"})
        ], className="card")
    
    # 타인 주변 표현 = 타인 전체 - 타인 중심
    # 간단히: 빈도 낮은 단어들
    similar_wordcloud = taste_analysis.get('similar_wordcloud', {})
    
    if not similar_wordcloud:
        sentence = "아직 데이터가 충분하지 않습니다."
        peripheral_words = {}
    else:
        # 하위 50% 단어들 (주변 표현)
        sorted_all = sorted(similar_wordcloud.items(), key=lambda x: x[1], reverse=True)
        midpoint = len(sorted_all) // 2
        peripheral_words = dict(sorted_all[midpoint:]) if len(sorted_all) > 3 else {}
        
        if peripheral_words:
            sentence = "아직 탐색 중인 표현들입니다."
        else:
            sentence = "주변 표현이 아직 충분하지 않습니다."
    
    return html.Div([
        html.Div("다른 사람에게서 스쳐간 표현", className="card-header"),
        html.P(sentence, style={
            "color": "rgba(245, 237, 220, 0.65)",
            "fontSize": "14px",
            "lineHeight": "1.7",
            "padding": "32px 24px 16px 24px",
            "textAlign": "center"
        }),
        _create_wordcloud_display(peripheral_words, max_words=10) if peripheral_words else None
    ], className="card")


def _create_wordcloud_panel(taste_analysis, username="사용자"):
    """다른 사람들이 자주 쓰는 표현 - 워드클라우드 (가로 길게)"""
    if not taste_analysis:
        return html.Div([
            html.Div("다른 사람들이 자주 쓰는 표현", className="card-header"),
            html.P("5개 이상 기록하면 분석이 시작됩니다", 
                  style={"textAlign": "center", "color": "rgba(245, 237, 220, 0.5)", "padding": "60px 20px", "fontSize": "16px"})
        ], className="card")
    
    similar_wordcloud = taste_analysis.get('similar_wordcloud', {})
    
    if not similar_wordcloud:
        sentence = "같은 노트를 기록한 사용자가 아직 없습니다."
    else:
        # 상위 2-3개 단어 추출
        sorted_words = sorted(similar_wordcloud.items(), key=lambda x: x[1], reverse=True)[:3]
        word_names = [word for word, _ in sorted_words]
        
        if len(word_names) >= 2:
            word_text = f"{word_names[0]}, {word_names[1]}"
        else:
            word_text = f"{word_names[0]}"
        
        sentence = f"같은 노트를 기록한 사람들은 {word_text} 같은 표현을 자주 사용했습니다."
    
    return html.Div([
        html.Div("다른 사람들이 자주 쓰는 표현", className="card-header"),
        html.P(sentence, style={
            "color": "rgba(245, 237, 220, 0.8)",
            "fontSize": "18px",
            "lineHeight": "1.6",
            "padding": "32px 24px 16px 24px",
            "textAlign": "center",
            "fontWeight": "400"
        }),
        _create_wordcloud_display(similar_wordcloud, max_words=20) if similar_wordcloud else None
    ], className="card")


def _create_my_expression_panel(taste_analysis, username="사용자"):
    """나의 표현 요약 - memo 워드클라우드"""
    if not taste_analysis:
        return html.Div([
            html.P("5개 이상 기록하면 취향 분석이 시작됩니다", 
                  style={"textAlign": "center", "color": "rgba(245, 237, 220, 0.5)", "padding": "40px"})
        ], className="card")
    
    memo_wordcloud = taste_analysis.get('memo_wordcloud', {})
    
    return html.Div([
        html.H3(f"{username}님은 이런 표현을 많이 사용해요", 
               style={"color": "rgba(245, 237, 220, 0.9)", "marginBottom": "24px", "textAlign": "center", "fontSize": "18px", "fontWeight": "500"}),
        _create_wordcloud_display(memo_wordcloud, max_words=20)
    ], className="card")


def _create_similar_expression_panel(taste_analysis, username="사용자"):
    """취향 확장 - 유사 사용자 memo 워드클라우드"""
    if not taste_analysis:
        return html.Div([
            html.P("5개 이상 기록하면 취향 확장 정보가 제공됩니다", 
                  style={"textAlign": "center", "color": "rgba(245, 237, 220, 0.5)", "padding": "40px"})
        ], className="card")
    
    similar_wordcloud = taste_analysis.get('similar_wordcloud', {})
    
    return html.Div([
        html.H3("다른 기록에서는", 
               style={"color": "rgba(245, 237, 220, 0.75)", "marginBottom": "8px", "textAlign": "center", "fontSize": "18px", "fontWeight": "500"}),
        html.P("이런 표현도 있었어요", 
              style={"color": "rgba(245, 237, 220, 0.5)", "marginBottom": "24px", "textAlign": "center", "fontSize": "15px"}),
        _create_wordcloud_display(similar_wordcloud, max_words=15)
    ], className="card")


def _create_survey_button():
    """설문 참여 링크 - Footer 스타일"""
    return html.Div([
        html.A(
            "📝 설문 참여",
            href="https://docs.google.com/forms/d/e/1FAIpQLSc07j2mn8bWEfuJr2-Zj6MtJqJyZfdiUCHz0wzRmi_9-6V-uw/viewform?usp=header",
            target="_blank",
            style={
                "textDecoration": "none",
                "fontSize": "13px",
                "color": "rgba(245, 237, 220, 0.5)",
                "transition": "color 0.2s ease"
            },
            className="survey-link"
        )
    ], style={
        "textAlign": "center",
        "padding": "40px 20px 20px",
        "marginTop": "80px",
        "borderTop": "1px solid rgba(255, 215, 0, 0.05)"
    })


def _render_records(records):
    """기록 목록 렌더링"""
    if not records or len(records) == 0:
        return html.Div([
            html.Div([
                html.P("📝", style={"fontSize": "48px", "marginBottom": "16px"}),
                html.P("아직 기록이 없습니다", 
                      style={"color": "#FFECB3", "marginBottom": "20px"}),
                dcc.Link("첫 기록 작성하기", href="/record", className="btn-primary")
            ], style={"textAlign": "center", "padding": "60px 20px"})
        ], className="card")
    
    # 영문 → 한글 매핑
    taste_labels = {
        "sweet": "스윗",
        "spicy": "스파이시",
        "fruity": "프루티",
        "nutty": "너티",
        "smoky": "스모키",
        "floral": "플로럴",
        "oaky": "우디",
        "peaty": "피트",
    }
    
    record_cards = []
    for record in records:
        taste_notes = record.get('taste_notes', [])
        rating = record.get('rating', 3)
        memo = record.get('memo', '')
        date = record.get('date', '')
        record_id = record.get('id', record.get('timestamp', ''))
        
        taste_badges = [
            html.Span(taste_labels.get(taste, taste), className="taste-badge")
            for taste in taste_notes
        ]
        
        card = html.Div([
            html.Div([
                html.H3(record.get('whiskey_name', '이름 없음'), 
                       style={"marginBottom": "12px", "fontSize": "22px", "color": "#FFD700"}),
                html.Div(taste_badges, style={"marginBottom": "12px"}),
                html.Div("⭐" * rating, style={"fontSize": "20px", "marginBottom": "12px"}),
                html.P(memo, style={"color": "#FFECB3", "marginBottom": "12px", 
                                   "whiteSpace": "pre-wrap"}) if memo else None,
                html.Div([
                    html.Span(f"📅 {date}", 
                             style={"color": "rgba(245, 237, 220, 0.5)", "fontSize": "14px"}),
                    html.Div([
                        html.Button("수정", 
                                   id={"type": "edit-btn", "index": str(record_id)},
                                   className="btn-sm-inline record-action-btn",
                                   style={"padding": "6px 14px", "fontSize": "13px", "marginRight": "8px"}),
                        html.Button("삭제",
                                   id={"type": "delete-btn", "index": str(record_id)},
                                   className="btn-sm-inline record-action-btn",
                                   style={"padding": "6px 14px", "fontSize": "13px", "marginRight": "8px"}),
                        html.Button("유사 리뷰",
                                   id={"type": "similar-review-btn", "index": str(record_id)},
                                   className="btn-sm-inline record-action-btn",
                                   style={"padding": "6px 14px", "fontSize": "13px"})
                    ], style={"display": "flex", "gap": "8px"})
                ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginTop": "16px", "paddingTop": "16px", "borderTop": "1px solid rgba(255, 215, 0, 0.1)"}),
                # 유사 리뷰 워드클라우드 영역
                html.Div(
                    id={"type": "similar-review-content", "index": str(record_id)},
                    style={"display": "none", "marginTop": "20px", "paddingTop": "20px",
                           "borderTop": "1px solid rgba(255, 215, 0, 0.1)"}
                ),
                # 저장된 키워드 표시 영역 (유사 리뷰용)
                html.Div(
                    id={"type": "record-saved-keywords", "index": str(record_id)},
                    style={"marginTop": "12px"}
                )
            ])
        ], className="card", style={"marginBottom": "20px"})
        
        record_cards.append(card)
    
    return record_cards


def _create_login_required_page():
    """로그인 필요 페이지"""
    return html.Div([
        html.Div([
            html.H2("🔒", style={"fontSize": "64px", "marginBottom": "16px"}),
            html.H3("로그인이 필요합니다", 
                   style={"marginBottom": "16px", "color": "#FFD700"}),
            html.P("이 페이지를 이용하려면 로그인해주세요", 
                  style={"color": "#FFECB3", "marginBottom": "24px"}),
            html.Button(
                "카카오 로그인",
                id="kakao-login-btn",
                className="btn-primary btn-large",
                style={"cursor": "pointer"}
            )
        ], className="card", style={"textAlign": "center", "maxWidth": "400px", 
                                    "margin": "100px auto"})
    ])


def create_message(msg_type, title, description=""):
    """메시지 컴포넌트"""
    icons = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️"
    }
    
    colors = {
        "success": "#10b981",
        "error": "#ef4444",
        "warning": "#f59e0b",
        "info": "#3b82f6"
    }
    
    return html.Div([
        html.Div([
            html.Span(icons.get(msg_type, "ℹ️"), 
                     style={"fontSize": "24px", "marginRight": "12px"}),
            html.Div([
                html.Strong(title, style={"display": "block", "marginBottom": "4px"}),
                html.Span(description, 
                         style={"fontSize": "14px", "color": "#FFECB3"}) if description else None
            ])
        ], style={
            "display": "flex",
            "alignItems": "center",
            "padding": "16px",
            "backgroundColor": f"{colors.get(msg_type, '#3b82f6')}15",
            "border": f"1px solid {colors.get(msg_type, '#3b82f6')}",
            "borderRadius": "8px",
            "marginBottom": "20px"
        })
    ])
#pragma once

#include <stddef.h>

struct Problem {
  const char *title;
  const char *answer;
  const char *serialText;
  const char *oledLines[5];
};

// 문제를 교체할 때는 이 배열만 수정하면 됩니다.
// serialText에는 문제 설명만, oledLines에는 보기/예시/분석 대상을 넣습니다.
// OLED 한 줄은 ASCII 16자 이내가 가장 읽기 좋습니다.
constexpr Problem PROBLEMS[] = {
    {
        "The Word",
        "Aegis{4}",
        "[01] The Word\n"
        "Aegis의 올바른 발음을 OLED 보기에서 골라 FLAG로 제출하세요.\n"
        "형식: Aegis{번호}",
        {"1) eye-gis", "2) ay-gis", "3) age-is", "4) ee-jis", "answer: number"},
    },
    {
        "CQ CQ CQ",
        "Aegis{CQCQCQDEAEGISAEGISAR}",
        "[02] CQ CQ CQ\n"
        "OLED에 표시된 통신 부호를 평문으로 복원해 FLAG로 제출하세요.",
        {"-.-. --.- -.-.", "--.- -.-. --.-", "-.. . .- . --.", ".. ... .- . --.", ".. ... .- .-."},
    },
    {
        "Decode",
        "Aegis{D0_Y0u_Kn0W_Wh@T_3nC0dInG_1s?}",
        "[03] Decode\n"
        "OLED의 문자열은 어떤 인코딩 결과입니다. 원문을 복원해 제출하세요.",
        {"QWVnaXN7RDBfWTB", "1X0tuMFdfV2hAVF", "8zbkMwZEluR18xcz", "99", "hint: base64"},
    },
    {
        "King Caesar",
        "Aegis{C0ngr@tU1AtI0nS_Y0u_h@cK3D_@11_Th3s3_d3vIc3s}",
        "[04] King Caesar\n"
        "OLED의 암호문에 고전 치환을 적용해 FLAG를 복원하세요.",
        {"Dhjlv{F0qju@wX1", "DwL0qV_B0x_k@fN", "3G_@11_Wk3v3_g3", "yLf3v}", "hint: shift -3"},
    },
};

constexpr size_t SERIAL_PROBLEM_COUNT = sizeof(PROBLEMS) / sizeof(PROBLEMS[0]);
constexpr size_t TOTAL_CHALLENGE_COUNT = SERIAL_PROBLEM_COUNT + 1; // Hidden Access
constexpr size_t HIDDEN_ACCESS_INDEX = SERIAL_PROBLEM_COUNT;

static_assert(TOTAL_CHALLENGE_COUNT == 5, "Rev.3 has five status LEDs");

// 미니게임 목표 기록 달성 후 보여줄 Hidden Access 힌트. 추후 문제에 맞게 교체하세요.
constexpr const char *MINIGAME_REWARD_LINE_1 = "front pads speak";
constexpr const char *MINIGAME_REWARD_LINE_2 = "when 2 meet";


#pragma once

#include <stddef.h>
#include <stdint.h>

constexpr uint8_t PROBLEM_STORAGE_VERSION = 1;
constexpr size_t PROBLEM_TITLE_SIZE = 24;
constexpr size_t PROBLEM_ANSWER_SIZE = 80;
constexpr size_t PROBLEM_TEXT_SIZE = 256;
constexpr size_t PROBLEM_OPTION_SIZE = 24;
constexpr uint8_t PROBLEM_OPTION_MAX = 4;

struct Problem {
  uint8_t version;
  char type; // F: FLAG, C: multiple choice
  uint8_t optionCount;
  char title[PROBLEM_TITLE_SIZE];
  char answer[PROBLEM_ANSWER_SIZE];
  char serialText[PROBLEM_TEXT_SIZE];
  char oledLines[PROBLEM_OPTION_MAX][PROBLEM_OPTION_SIZE];
};

// NVS에 사용자 문제가 없을 때 사용하눈 기본값입니다.
constexpr Problem DEFAULT_PROBLEMS[] = {
    {
        PROBLEM_STORAGE_VERSION, 'F', 4,
        "The Word",
        "Aegis{4}",
        "[01] The Word\nAegis의 올바른 발음을 OLED 보기에서 골라 FLAG로 제출하세요.\n형식: Aegis{번호}",
        {"1) eye-gis", "2) ay-gis", "3) age-is", "4) ee-jis"},
    },
    {
        PROBLEM_STORAGE_VERSION, 'F', 4,
        "CQ CQ CQ",
        "Aegis{CQCQCQDEAEGISAEGISAR}",
        "[02] CQ CQ CQ\nOLED에 표시된 통신 부호룰 평문으로 복원해 FLAG로 제출하세요.",
        {"-.-. --.- -.-.", "--.- -.-. --.-", "-.. . .- . --.", ".. ... .- . --."},
    },
    {
        PROBLEM_STORAGE_VERSION, 'F', 4,
        "Decode",
        "Aegis{D0_Y0u_Kn0W_Wh@T_3nC0dInG_1s?}",
        "[03] Decode\nOLED의 문자열은 어떤 인코딩 결과입니다. 원문을 복원해 제출하세요.",
        {"QWVnaXN7RDBfWTB", "1X0tuMFdfV2hAVF", "8zbkMwZEluR18xcz", "99"},
    },
    {
        PROBLEM_STORAGE_VERSION, 'F', 4,
        "King Caesar",
        "Aegis{C0ngr@tU1AtI0nS_Y0u_h@cK3D_@11_Th3s3_d3vIc3s}",
        "[04] King Caesar\nOLED의 암호문에 고전 치환을 적용해 FLAG랄 복원하세요.",
        {"Dhjlv{F0qju@wX1", "DwL0qV_B0x_k@fN", "3G_@11_Wk3v3_g3", "yLf3v}"},
    },
};

constexpr size_t SERIAL_PROBLEM_COUNT =
    sizeof(DEFAULT_PROBLEMS) / sizeof(DEFAULT_PROBLEMS[0]);
constexpr size_t TOTAL_CHALLENGE_COUNT = SERIAL_PROBLEM_COUNT + 1; // Hidden Access
constexpr size_t HIDDEN_ACCESS_INDEX = SERIAL_PROBLEM_COUNT;

static_assert(TOTAL_CHALLENGE_COUNT == 5, "Rev.3 has five status LEDs");

constexpr const char *MINIGAME_REWARD_LINE_1 = "shorting board Front C0-C2";

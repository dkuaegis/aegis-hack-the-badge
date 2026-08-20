#pragma once

#include <stddef.h>
#include <stdint.h>

constexpr uint8_t PROBLEM_STORAGE_VERSION = 2;
constexpr size_t PROBLEM_TITLE_SIZE = 24;
constexpr size_t PROBLEM_ANSWER_SIZE = 80;
constexpr size_t PROBLEM_TEXT_SIZE = 256;
constexpr size_t PROBLEM_OPTION_SIZE = 24;
constexpr uint8_t PROBLEM_OPTION_MAX = 4;

constexpr uint8_t MISSION_LEAKED = 0;
constexpr uint8_t MISSION_DEBUG = 1;
constexpr uint8_t MISSION_MAINTENANCE = 2;
constexpr uint8_t MISSION_LEGACY_AUTH = 3;

struct Problem {
  uint8_t version;
  char type; // F: FLAG, C: multiple choice
  uint8_t optionCount;
  char title[PROBLEM_TITLE_SIZE];
  char answer[PROBLEM_ANSWER_SIZE];
  char serialText[PROBLEM_TEXT_SIZE];
  char oledLines[PROBLEM_OPTION_MAX][PROBLEM_OPTION_SIZE];
};

// NVS에 현재 version의 문제가 없을 때 사용하는 기본값입니다.
constexpr Problem DEFAULT_PROBLEMS[] = {
    {
        PROBLEM_STORAGE_VERSION, 'F', 4,
        "LEAKED TRANSMISSION",
        "Aegis{S3r14l_L34k}",
        "[MISSION 01 // LEAKED TRANSMISSION]\n통신 기록에서 정체불명의 데이터가 발견되었습니다.\nHEX 데이터를 원래 메시지로 복원해 FLAG를 제출하세요.",
        {"LEAKED", "TRANSMISSION", "", "HEX -> TEXT"},
    },
    {
        PROBLEM_STORAGE_VERSION, 'F', 4,
        "DEBUG LEFT ON",
        "Aegis{D3bug_L0gs_4r3_D4ng3r0us}",
        "[MISSION 02 // DEBUG LEFT ON]\n운영 장치에 디버그 기능이 남아 있습니다.\n콘솔을 조사해 노출된 FLAG를 찾으세요.\n먼저 사용 가능한 명령을 확인하세요.",
        {"DEBUG", "LEFT ON", "EXPLORE", "THE CONSOLE"},
    },
    {
        PROBLEM_STORAGE_VERSION, 'F', 4,
        "MAINTENANCE",
        "Aegis{H1dd3n_D14gn0st1c}",
        "[MISSION 03 // MAINTENANCE]\n운영 펌웨어에 개발용 유지보수 기능이 남아 있습니다.\n일반 도움말에 없는 인터페이스를 찾아 FLAG를 획득하세요.",
        {"MAINTENANCE", "", "INTERFACE", "HIDDEN"},
    },
    {
        PROBLEM_STORAGE_VERSION, 'F', 4,
        "LEGACY AUTH",
        // Dynamic 인증 성공 후 출력할 reward FLAG입니다.
        "Aegis{L3g4cy_4uth_1s_N0t_S4f3}",
        "[MISSION 04 // LEGACY AUTH]\n관리자 인증에 오래된 방식이 사용되고 있습니다.\n과거 기록을 분석해 현재 challenge의 response를 계산하세요.",
        {"LEGACY AUTH", "", "ANALYZE", "THE PATTERN"},
    },
};

constexpr size_t SERIAL_PROBLEM_COUNT =
    sizeof(DEFAULT_PROBLEMS) / sizeof(DEFAULT_PROBLEMS[0]);
constexpr size_t TOTAL_CHALLENGE_COUNT = SERIAL_PROBLEM_COUNT + 1; // Hidden Access
constexpr size_t HIDDEN_ACCESS_INDEX = SERIAL_PROBLEM_COUNT;

static_assert(TOTAL_CHALLENGE_COUNT == 5, "Rev.3 has five status LEDs");

constexpr const char *MINIGAME_REWARD_LINE_1 = "shorting board Front C0-C2";

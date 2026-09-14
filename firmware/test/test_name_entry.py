"""Compile the actual name-entry handlers with host button/BLE stubs."""

import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / "src/main.cpp").read_text()
state = "struct NameEntryState {" + source.split("struct NameEntryState {", 1)[1].split("} nameEntry;", 1)[0] + "} nameEntry;"
record = "struct ScoreRecord {" + source.split("struct ScoreRecord {", 1)[1].split("struct NameEntryState", 1)[0]
begin = "void beginNameEntry(" + source.split("void beginNameEntry(", 1)[1].split("\nbool finishNameEntry", 1)[0]
finish = "bool finishNameEntry() {" + source.split("bool finishNameEntry() {", 1)[1].split("\nvoid reportScore", 1)[0]
update = "bool updateNameEntry() {" + source.split("bool updateNameEntry() {", 1)[1].split("\nvoid enterGame", 1)[0]
score_command = "bool parseScoreGame(" + source.split("bool parseScoreGame(", 1)[1].split("\nvoid handleBleCommand", 1)[0]
harness = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include "logic.h"
constexpr uint8_t LEADERBOARD_NAME_LENGTH = 10;
constexpr uint32_t LONG_PRESS_MS = 700;
enum class ScoreGame { Flappy, Firewall, Tetris };
enum class Screen { Home, Game, FirewallGame, TetrisGame };
enum class GamePhase { Over, NameEntry };
enum class FirewallPhase { Over, NameEntry };
enum class TetrisPhase { Over, NameEntry };
Screen screen = Screen::Game;
GamePhase gamePhase = GamePhase::Over;
struct { uint16_t score = 42; } game;
struct { uint16_t score = 42; FirewallPhase phase = FirewallPhase::Over; } firewall;
struct { uint16_t score = 42; TetrisPhase phase = TetrisPhase::Over; } tetris;
struct Button {
  bool raw=false, stable=false, pressed=false, released=false;
  bool longPressed=false, longFired=false;
} left, right, ok;
uint32_t now = 0;
uint32_t millis() { return now; }
bool bleConnected=true, bleAuthenticated=true, bleStatusDirty=false;
std::string submission;
void bleSendLine(const char *line) { submission = line; }
const char *scoreGameName(ScoreGame game) {
  return game == ScoreGame::Flappy ? "flappy" : game == ScoreGame::Firewall ? "firewall" : "tetris";
}
void beep(int, int) {}
void drawNameEntry() {}
void drawHome() {}
void drawGameOver() {}
void drawFirewallOver() {}
void drawTetrisOver() {}
'''
harness += record + "ScoreRecord highScores[3];\n" + state + begin + finish + update + score_command + r'''
void reset() {
  left = right = ok = Button{};
  nameEntry = NameEntryState{};
  nameEntry.score = 42;
  bleConnected = bleAuthenticated = true;
  submission.clear();
  now = 0;
  screen = Screen::Game;
  gamePhase = GamePhase::Over;
  firewall.phase = FirewallPhase::Over;
  tetris.phase = TetrisPhase::Over;
}
void command(const char *text) {
  char line[80];
  snprintf(line, sizeof(line), "%s", text);
  handleScoreCommand(line);
}
int main() {
  reset();
  assert(strcmp(nameEntry.name, " ") == 0);
  ok.longPressed = true;
  assert(!updateNameEntry() && submission.empty()); // An empty name cannot be saved.
  ok = Button{};
  right.pressed = true;
  assert(!updateNameEntry() && strcmp(nameEntry.name, "A") == 0);
  right = Button{};
  ok.longPressed = true;
  assert(!updateNameEntry() && submission.empty()); // Current character is unconfirmed.
  ok = Button{};
  ok.released = true;
  assert(!updateNameEntry() && nameEntry.cursor == 1);
  assert(strcmp(nameEntry.name, "A ") == 0);
  ok = Button{};
  ok.longPressed = true;
  assert(updateNameEntry() && submission == "SCORE_SUBMIT flappy 42 A");

  reset();
  const char *name = " A  B ";
  for (unsigned i = 0; name[i]; ++i) {
    nameEntry.name[nameEntry.cursor] = name[i];
    ok.released = true;
    assert(!updateNameEntry());
  }
  ok = Button{};
  right.pressed = true; // Even an edited but unconfirmed final character is excluded.
  assert(!updateNameEntry());
  right = Button{};
  ok.longPressed = true;
  assert(updateNameEntry() && submission == "SCORE_SUBMIT flappy 42  A  B ");

  reset();
  ok.released = true;
  assert(!updateNameEntry());
  ok = Button{};
  ok.longPressed = true;
  assert(!updateNameEntry() && submission.empty()); // Whitespace-only name is invalid.

  reset();
  strcpy(nameEntry.name, "0123456789");
  nameEntry.cursor = 9;
  ok.released = true;
  assert(!updateNameEntry() && nameEntry.cursor == 10 && submission.empty());
  ok = Button{};
  right.pressed = true;
  assert(!updateNameEntry() && strcmp(nameEntry.name, "0123456789") == 0);
  right = Button{};
  ok.longPressed = true;
  assert(updateNameEntry() && submission == "SCORE_SUBMIT flappy 42 0123456789");

  for (int index = 0; index < 3; ++index) {
  reset();
  const auto gameId = static_cast<ScoreGame>(index);
  const Screen gameScreen = static_cast<Screen>(index + 1);
  screen = gameScreen;
  char line[80];
  snprintf(line, sizeof(line), "score name %s 42", scoreGameName(gameId));
  command(line);
  assert(nameEntry.game == gameId && strcmp(nameEntry.name, " ") == 0);
  submission.clear();
  left.raw = right.raw = left.stable = right.stable = true;
  assert(!updateNameEntry());
  now = 699;
  assert(!updateNameEntry() && !nameEntry.cancelled);
  right = Button{}; // An interrupted chord must restart its timer.
  assert(!updateNameEntry());
  right.raw = right.stable = true;
  now = 1000;
  assert(!updateNameEntry());
  now = 1699;
  assert(!updateNameEntry() && !nameEntry.cancelled);
  now = 1700;
  ok.longPressed = true; // Cancellation wins over a simultaneous save.
  assert(!updateNameEntry() && nameEntry.cancelled && submission.empty());
  left.raw = right.raw = false; // Wait for debounced release too.
  assert(!updateNameEntry() && screen == gameScreen);
  left = right = ok = Button{};
  assert(!updateNameEntry() && screen == Screen::Home && submission.empty());

  // Sync accepts spaces, lower authoritative scores, and an empty server DB.
  snprintf(line, sizeof(line), "score sync %s 99  A  B ", scoreGameName(gameId));
  command(line);
  assert(highScores[index].score == 99 && strcmp(highScores[index].name, " A  B ") == 0);
  snprintf(line, sizeof(line), "score sync %s 80 LOWER", scoreGameName(gameId));
  command(line);
  assert(highScores[index].score == 80);
  snprintf(line, sizeof(line), "score sync %s 100 A\tB", scoreGameName(gameId));
  command(line);
  assert(highScores[index].score == 80);
  snprintf(line, sizeof(line), "score sync %s 0 ---", scoreGameName(gameId));
  command(line);
  assert(highScores[index].score == 0 && strcmp(highScores[index].name, "---") == 0);
  }

  reset();
  bleConnected = false;
  assert(!updateNameEntry() && nameEntry.cancelled);
  assert(!updateNameEntry() && screen == Screen::Home && submission.empty());
  reset();
  bleAuthenticated = false;
  assert(finishNameEntry() && submission.empty());
}
'''
with tempfile.TemporaryDirectory() as directory:
    cpp = Path(directory) / "name_entry.cpp"
    binary = Path(directory) / "name_entry"
    cpp.write_text(harness)
    subprocess.run([os.environ.get("CXX", "clang++"), "-std=c++17",
                    f"-I{root / 'src'}", str(cpp), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("firmware name-entry save/cancel/disconnect and server score sync tests: OK")

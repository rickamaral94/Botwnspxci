// The Expansion Pass from its own package: the AddOnContent CNMTs of Breath of the Wild, the pack with the data chosen
// (System/AocVersion.txt with Pack/), the Ballad's unlock alone refused, another game's DLC refused; and its aoc.bin
// through RomfsFeed and runtime/romfs_build.c, the same image the app builds from the extracted folder.
#include "cnmt.h"
#include "nximport.h"
#include "romfs_build.h"
#include "romfs_feed.h"
#include "synth.h"
#include "test.h"

#include <cstring>
#include <sys/stat.h>

using namespace nx;

std::string temp_dir();
void rm_tree(const std::string &p);
synth::Bytes read_file(const std::string &p);

namespace {

const uint64_t DLC_DATA = 0x01007EF00011F001ull, DLC_UNLOCK = 0x01007EF00011F002ull;

struct DlcFixture {
    std::mt19937_64 rng{555};
    synth::Keys keys{rng};
    synth::Files data = {{"System/AocVersion.txt", {'3'}},
                         {"Pack/AocMainField.pack", synth::random_bytes(rng, 30000)},
                         {"Pack/Dungeon120.pack", synth::random_bytes(rng, 9000)},
                         {"Movie/Demo600_0.mp4", synth::random_bytes(rng, 2000)}};
    synth::Files unlock = {{"System/AocVersion.txt", {'3'}}};

    // one AddOnContent title: its CNMT in a Meta NCA, its data NCA (a RomFS only), a ticket when it uses a title key
    synth::Files aoc(uint64_t title, uint64_t app, const synth::Files &files, bool rights) {
        synth::NcaSpec d;
        d.type = ContentType::Data;
        d.title_id = title;
        d.rights = rights;
        d.sections = {{true, synth::romfs(files)}};
        synth::Nca data_nca = synth::nca(keys, d, rng);
        char name[64];
        snprintf(name, sizeof name, "AddOnContent_%016llx.cnmt", (unsigned long long)title);
        synth::NcaSpec m;
        m.type = ContentType::Meta;
        m.title_id = title;
        m.sections = {{false, synth::pfs0({{name, synth::cnmt(title, 0x30000, META_ADDON, app, {{data_nca.bytes, CNT_DATA}})}})}};
        synth::Nca meta = synth::nca(keys, m, rng);
        synth::Files out = {{synth::nca_name(data_nca.bytes, false), data_nca.bytes}, {synth::nca_name(meta.bytes, true), meta.bytes}};
        if (rights) {
            uint8_t enc[16];
            aes_ecb_encrypt(keys.titlekek[0], data_nca.title_key.data(), enc, 16);
            out.push_back({hex(data_nca.rights_id, 16) + ".tik", synth::ticket(data_nca.rights_id, enc, true)});
        }
        return out;
    }
    ImportInput input(const synth::Files &pkg) {
        ImportInput in;
        in.base = std::make_shared<MemReader>(synth::pfs0(pkg), "dlc.nsp");
        std::string k = keys.prod_keys();
        in.prod_keys = std::make_shared<MemReader>(synth::Bytes(k.begin(), k.end()), "prod.keys");
        return in;
    }
};

}  // namespace

TEST(dlc_both_packs_data_chosen) {
    DlcFixture fx;
    synth::Files pkg = fx.aoc(DLC_UNLOCK, BOTW_TITLE_ID, fx.unlock, true);
    for (auto &f : fx.aoc(DLC_DATA, BOTW_TITLE_ID, fx.data, true)) pkg.push_back(f);
    DlcImporter dlc(fx.input(pkg));
    CHECK(dlc.title_id() == DLC_DATA);
    CHECK(dlc.version() == 0x30000);
    REQUIRE(dlc.romfs().files.size() == fx.data.size());
    for (size_t i = 0; i < dlc.romfs().files.size(); i++)
        for (auto &f : fx.data)
            if (f.first == dlc.romfs().files[i].path) {
                synth::Bytes b(f.second.size());
                dlc.read_romfs(i, b.data(), b.size(), 0);
                CHECK(b == f.second);
            }
    // aoc.bin through the feed: the image runtime/romfs_build.c makes from the same files in a folder
    std::string dir = temp_dir();
    for (auto &f : fx.data) {
        std::string p = dir + "/romfs/" + f.first;
        for (size_t s = p.find('/', dir.size() + 1); s != std::string::npos; s = p.find('/', s + 1)) mkdir(p.substr(0, s).c_str(), 0755);
        FILE *o = fopen(p.c_str(), "wb");
        fwrite(f.second.data(), 1, f.second.size(), o);
        fclose(o);
    }
    char why[256] = "";
    REQUIRE(romfs_build((dir + "/romfs").c_str(), (dir + "/folder.bin").c_str(), nullptr, why, sizeof why));
    std::vector<RomfsEntry> entries;
    for (auto &f : dlc.romfs().files) entries.push_back({f.path.c_str(), f.size});
    RomfsFeed feed(dlc, nullptr);
    REQUIRE(romfs_build_entries(entries.data(), int(entries.size()), &RomfsFeed::open_fd, &feed, (dir + "/aoc.bin").c_str(),
                                nullptr, nullptr, nullptr, why, sizeof why));
    CHECK(feed.finish() == nullptr);
    CHECK(read_file(dir + "/aoc.bin") == read_file(dir + "/folder.bin"));
    rm_tree(dir);
}

TEST(dlc_refusals) {
    DlcFixture fx;
    bool unlock_only = false;
    try {
        DlcImporter d(fx.input(fx.aoc(DLC_UNLOCK, BOTW_TITLE_ID, fx.unlock, false)));
    } catch (const DlcUnlockOnly &) {
        unlock_only = true;
    }
    CHECK(unlock_only);
    std::string e = ERROR_OF(DlcImporter{fx.input(fx.aoc(0x0100000000011001ull, 0x0100000000010000ull, fx.data, false))});
    CHECK(contains(e, "is not a DLC of Breath of the Wild"));
    CHECK(contains(e, "0100000000011001"));
    // the base game's own package isn't a DLC either
    synth::GameSpec g;
    g.exefs = synth::sample_exefs(fx.rng), g.romfs = synth::sample_romfs(fx.rng);
    CHECK(contains(ERROR_OF(DlcImporter{fx.input(synth::game(fx.keys, g, fx.rng).package)}), "is not a DLC"));
}

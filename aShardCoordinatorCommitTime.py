import re
import sys
import json
import numpy as np


'''
2016-09-21 20:10:15,001 | INFO  | ult-dispatcher-4 | Shard |
226 - org.opendaylight.controller.sal-akka-raft - 1.2.5.SNAPSHOT |
Readying member-1-txn-1 org.opendaylight.controller.cluster.datastore.Shard@1c96ff11 363111960622734
'''


def np_recount_mean_err(np_array):
    return {
        "means": np.mean(np_array),
        "stderr": np.std(np_array),
    }


def pre_process(lines):
    current = "BlankHead"
    pos = 0
    result = {
        current: {
            "pos": pos,
            "lines": []
        }
    }
    pattern_field = r"\s*\[\s*(.*?)\s*\]$"
    p = re.compile(pattern_field)

    for line in lines:
        m = p.match(line)
        if m is not None:
            current = m.groups()[0]
            if current not in result:
                pos += 1
                result[current] = {
                    "pos": pos,
                    "lines": []
                }
        else:
            result[current]["lines"].append(line)

    del result["BlankHead"]
    return result


def analyze(line):
    groups = line.split("|")
    if len(groups) == 6 and groups[3].strip() == "Shard":
        info = groups[5].strip()
        infos = info.split(" ")
        if len(infos) == 4:
            info_analyze = {
                "method": infos[0],
                "transid": infos[1],
                "shardname": infos[2],
                "timestamp": long(infos[3]),
            }
            return info_analyze

    return None


def analyze_all(lines):
    """

    :param lines: lines in group
    :return: a info dictionary
    {
        shardname : {
            "tests": [
                { "canCommiting" : ts, "preCommit": ts, "continueCommit": ts },
                ...
            ],
            ...
        },
        ...
    }
    """
    info_all = {}
    for line in lines:
        info = analyze(line)
        if info is not None:
            '''
            put_into_dict_in_dict(info_all, info["shardname"], info["method"], info["timestamp"])
            '''
            shard_name = info["shardname"]
            method = info["method"]
            times = info["timestamp"]

            if shard_name not in info_all:
                info_all[shard_name] = {"current": -1, "tests": []}

            if method == "canCommiting":
                info_all[shard_name]["current"] += 1
                info_all[shard_name]["tests"].append(dict())

            current = info_all[shard_name]["current"]
            if current >= 0:
                info_all[shard_name]["tests"][current][method] = times

    return info_all


def synthesize(infos):
    result = []
    for shard in infos:
        shard_info = dict()
        shard_info["name"] = shard
        shard_info["result"] = []
        t_cancommits = []
        t_precommits = []
        t_commits = []
        for test in infos[shard]["tests"]:
            t_cancommit = (test["preCommit"] - test["canCommiting"]) / 1000
            t_precommit = (test["continueCommit"] - test["preCommit"]) / 1000
            t_commit = (test["commited"] - test["continueCommit"]) / 1000

            t_cancommits.append(t_cancommit)
            t_precommits.append(t_precommit)
            t_commits.append(t_commit)

            '''shard_info["result"].append({
                "1-canCommit": t_cancommit,
                "2-preCommit": t_precommit,
                "3-commit": t_commit,
            })'''

        npt_cancommits = np.array(t_cancommits)
        npt_precommits = np.array(t_precommits)
        npt_commits = np.array(t_commits)

        shard_info["recount"] = {
            "1-canCommit": np_recount_mean_err(npt_cancommits),
            "2-preCommit": np_recount_mean_err(npt_precommits),
            "3-commit": np_recount_mean_err(npt_commits),
        }
        result.append(shard_info)

    return result


def for_longest_commit_recount(syn_result):
    max_t = 0
    ret = None
    for shard_info in syn_result["results"]:
        total_means = sum([x["means"] for x in shard_info["recount"].values()])
        total_stderr = sum([x["stderr"] for x in shard_info["recount"].values()])
        if total_means > max_t:
            ret = dict(shard_info["recount"], **{"4-total": {"means": total_means, "stderr": total_stderr}})
            max_t = total_means

    return ret


def plot_recounts(plotting):
    import matplotlib.pyplot as plt

    fig = plt.figure()
    ax = fig.add_subplot(111)
    means_group = []
    std_group = []
    title_group = []
    for sb_plot in plotting:
        title_group.append(sb_plot["plot_name"])
        t_sorted = sorted(sb_plot["recount"].items(), key=lambda x: x[0])
        means_group.append([x[1]["means"] for x in t_sorted])
        std_group.append([x[1]["stderr"] for x in t_sorted])

    means_bar = zip(*[x for x in means_group])
    std_bar = zip(*[x for x in std_group])

    legends = ['canCommit', 'preCommit', 'commit', 'total']
    legends_rect_aid = []
    colors = ['c', 'm', 'red', 'black']
    ind = np.arange(len(plotting))
    width = 0.2

    for i in range(4):
        rect = ax.bar(ind + width * i, means_bar[i], width,
                      color=colors[i],
                      yerr=std_bar[i],
                      error_kw=dict(elinewidth=2,ecolor='red'))

        legends_rect_aid.append(rect[0])

    ax.set_xlim(-width,len(ind)+width)
    ax.set_ylabel('time(ms)')
    ax.set_title('commit timing report')
    ax.set_xticks(ind+width)
    xtickNames = ax.set_xticklabels(title_group)
    plt.setp(xtickNames, rotation=45, fontsize=10)
    plt.legend(legends_rect_aid, legends)
    plt.show()


def synthesize_all(ar_all_tuple, plot=True):
    syn_result = []
    plotting = []
    pattern_graph = r"g\{([^\}]*)\}.*$"
    p = re.compile(pattern_graph)

    for k, v in ar_all_tuple:
        syn_result.append(
            {
                "group_name": k,
                "results": synthesize(analyze_all(v["lines"])),
            }
        )

        if plot:
            m = p.match(k)
            if m is not None:
                plotting.append({
                    "plot_name": m.groups()[0],
                    "recount": for_longest_commit_recount(syn_result[-1])
                })

    if plot and len(plotting):
        plot_recounts(plotting)

    return syn_result


filename = sys.argv[1]

f = open(filename)
lines = f.readlines()
f.close()

grps = pre_process(lines)
grps_sort = sorted(grps.items(), key=lambda x: x[1]['pos'])

result = synthesize_all(grps_sort)

f = open("synthesize", "w")
json.dump(result, f, indent=4, sort_keys=True)
f.close()

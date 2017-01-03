import numpy as np
import re
import json


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
    ax.set_ylabel('time(us)')
    ax.set_title('commit timing report')
    ax.set_xticks(ind+width)
    xtickNames = ax.set_xticklabels(title_group)
    plt.setp(xtickNames, rotation=45, fontsize=10)
    plt.legend(legends_rect_aid, legends)
    plt.show()


def plot_graph(syn_results):
    plotting = []
    pattern_graph = r"g\{([^\}]*)\}.*$"
    p = re.compile(pattern_graph)

    for syn_result in syn_results:
        group_name = syn_result["group_name"]
        m = p.match(group_name)
        if m is not None:
            plotting.append({
                "plot_name": m.groups()[0],
                "recount": for_longest_commit_recount(syn_result)
            })

    if len(plotting):
        plot_recounts(plotting)


if __name__ == "__main__":
    f = open("synthesize")
    results = json.load(f)
    f.close()
    plot_graph(results)

#!/usr/bin/env python3

import subprocess
import json
import os.path
import graph_tool.all


def get_vertex(g, name2idx, v_prop, name):
    if name in name2idx:
        return name2idx[name]
    v = g.add_vertex()
    v_prop[v] = {'label': name}
    idx = g.vertex_index[v]
    name2idx[name] = idx
    return idx


def load():
    if os.path.exists('deps.json'):
        with open('deps.json', 'r') as f:
            deps = json.load(f)
        return deps
    else:
        return {}


def save(deps):
    with open('deps.json', 'w') as f:
        json.dump(deps, f, indent=2)


def fetch(deps):
    lst = subprocess.check_output(['apt-cache', 'search', '.']).decode()
    counter = 0
    lst = lst.split('\n')
    total = len(lst)
    counter = 0
    for pkg in lst:
        name = pkg.split(' ')[0]
        counter += 1
        print('[{}/{}] Fetching {}'.format(counter, total, name))
        if name in deps:
            continue
        if name == '':
            continue
        depends = subprocess.check_output([
            'apt-cache', 'depends', '--no-suggests', '--no-breaks',
            '--no-conflicts', '--no-pre-depends', name
        ]).decode()
        dep_list = []

        for dep in [dep for dep in depends.split('\n') if 'Depends:' in dep]:
            dep_name = dep.split(':')[1].strip()
            dep_list.append(dep_name)
        deps[name] = dep_list

        if counter % 10 == 0:
            save(deps)
    save(deps)
    return deps


def build(deps):
    g = graph_tool.Graph()
    name2idx = {}
    v_prop = g.new_vertex_property('object')
    total = len(deps)
    counter = 0

    for name, depends in deps.items():
        counter += 1
        print('[{}/{}] Building {}'.format(counter, total, name))
        src = get_vertex(g, name2idx, v_prop, name)
        edges = []
        for dep_name in depends:
            dst = get_vertex(g, name2idx, v_prop, dep_name)
            edges.append((src, dst))
        g.add_edge_list(edges)

    g.vertex_properties['info'] = v_prop
    return g


def transitive_closure(g):
    transitive = graph_tool.topology.transitive_closure(g)
    return transitive


def draw(g, output):
    v_prop = g.vertex_properties['info']
    #v_shape = g.vertex_properties['shape']
    #v_color = g.vertex_properties['color']
    #vprops = {'shape': v_shape}
    graph_tool.graphviz_draw(
        g,
        #    vcolor=v_color,
        #    vprops=vprops,
        size=(30, 30),
        overlap=False,
        output=output)


def print_node_id(g, output):
    v_prop = g.vertex_properties['info']

    with open(output, 'w') as f:
        for v in g.vertices():
            f.write('{}: {}\n'.format(v, v_prop[v]['label']))


def stats(deps, g, trans):
    size_table = list(map(lambda x: (x, len(deps[x])), deps))
    size_table.sort(key=lambda x: x[1], reverse=True)

    trans_size_table = []
    v_prop = g.vertex_properties['info']
    for v in trans.vertices():
        trans_size_table.append((v_prop[v]['label'], len(list(v.out_edges()))))
    trans_size_table.sort(key=lambda x: x[1], reverse=True)

    with open('direct.txt', 'w') as f:
        counter = 1
        f.write('{}, {}, {}\n'.format('Rank', 'name', 'size'))
        for name, size in size_table:
            f.write('{}, {}, {}\n'.format(counter, name, size))
            counter += 1
    with open('transitive.txt', 'w') as f:
        f.write('# Transitive Dependencies\n')
        counter = 1
        f.write('{}, {}, {}\n'.format('Rank', 'name', 'size'))
        for name, size in trans_size_table:
            f.write('{}, {}, {}\n'.format(counter, name, size))
            counter += 1


deps = load()
deps = fetch(deps)
g = build(deps)
transitive = transitive_closure(g)
stats(deps, g, transitive)
#draw(g, 'output.svg')
#print_node_id(g, 'labels.txt')

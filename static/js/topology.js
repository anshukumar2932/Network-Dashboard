// static/js/topology.js
(function () {
    'use strict';

    /* ═══════════════════════════════════════════════════════════════
       PUBLIC ENTRY POINT
       Call window.initTopology(config) from each page.
       config = {
           mode: 'dashboard' | 'fullscreen',
           cyContainer:   '#cy',
           loadingEl:     '#cy-loading' | '#loading',
           pingFlashEl:   '#pingFlash',
           syncBadgeEl:   '#syncBadge',
           fitBtn:        '#fitBtn',
           expandAllBtn:  '#expandAllBtn',
           collapseAllBtn:'#collapseAllBtn',
           resetLayoutBtn:'#resetLayoutBtn',
           lockLayoutBtn: '#lockLayoutBtn',
           pingBtn:       '#pingBtn',
           refreshBtn:    '#refreshBtn',
           searchInput:   '#searchInput',
           legendBox:     '#legendBox',
           legendToggle:  '#legendToggle',
           legendIcon:    '#legendIcon',
           nodeTooltip:   '#nodeTooltip',
           ctxMenu:       '#ctxMenu',
           modalOverlay:  '#linkModalOverlay',
           modalTitle:    '#linkModalTitle',
           modalBody:     '#linkModalBody',
           modalClose:    '#modalCloseBtn',
           minimapEl:     '#cy-minimap',          // optional
           kpiTotal:      '#kpiTotal',
           kpiUp:         '#kpiUp',
           kpiDown:       '#kpiDown',
           // dashboard-only
           alertList:     '#alertList',
           alertCount:    '#alertCount',
           categoryContainer: '#categoryContainer',
           categoryCount: '#categoryCount',
           downDevices:   '#downDevices',
           activeAlerts:  '#activeAlerts',
           lastPoll:      '#lastPoll',
           kpiAlerts:     '#kpiAlerts',
           siteInfoPanel: '#siteInfoPanel',
           // fullscreen-only
           alertPanel:    '#alertPanel',
            exitBtn:       '#exitBtn',
            categoryMenu:    '#categoryMenu',
            sharedLegend:    '#sharedLegend',
        }
    ═══════════════════════════════════════════════════════════════ */

    /* ── Register ELK ── */
    try {
        if (typeof CytoscapeELK !== 'undefined') cytoscape.use(CytoscapeELK);
        else if (typeof window.CytoscapeELK !== 'undefined') cytoscape.use(window.CytoscapeELK);
        else console.warn('[TOPOLOGY] ELK not found, will use fallback');
    } catch (e) { console.error('[TOPOLOGY] ELK register error:', e); }

    /* ═══════════════════════════════════════════════════════════════
       STATE
    ═══════════════════════════════════════════════════════════════ */
    let cy             = null;
    let ctxNode        = null;
    let saveTimer      = null;
    let layoutLocked   = false;
    let suppressSave   = false;
    let navInstance    = null;
    let cfg            = {};

    const collapsedNodes = new Set();
    let depthMap         = null;
    let childCountMap    = null;
    const childrenMap    = new Map();
    const parentMap      = new Map();

    /* smart collapse state */
    const hiddenCategories = new Set();

    /* carousel state (dashboard only) */
    let catCarouselData  = [];
    let alertInterval    = null;
    let alertPaused      = false;
    const ALERT_HEIGHT   = 54;

    /* monitor banner state (dashboard only) */
    let lastHeartbeat      = 0;
    let monitorBannerState = 'ok';

    /* ── Helpers ── */
    function $el(sel) { return sel ? document.querySelector(sel) : null; }
    function getCsrfToken() { return document.querySelector('meta[name="csrf-token"]')?.content || ''; }

    /* ═══════════════════════════════════════════════════════════════
       RESOLVED ELEMENTS — lookups happen once at init, not per-frame
    ═══════════════════════════════════════════════════════════════ */
    const el = {};

    /* ═══════════════════════════════════════════════════════════════
       CYTOSCAPE STYLE
    ═══════════════════════════════════════════════════════════════ */
    const CY_STYLE = [
        { selector: 'node', style: {
            'label': 'data(label)', 'text-valign': 'bottom', 'text-halign': 'center',
            'font-size': '11px', 'font-weight': '600', 'color': '#1e293b',
            'text-wrap': 'wrap', 'text-max-width': '100px', 'text-margin-y': '5px',
            'width': '42px', 'height': '42px', 'border-width': '4px',
            'border-color': '#e2e8f0', 'border-style': 'solid', 'background-color': '#e2e8f0',
            'shadow-blur': 8, 'shadow-color': 'rgba(0,0,0,.12)',
            'shadow-offset-x': 0, 'shadow-offset-y': 2,
            'transition-property': 'border-color,border-width,width,height,border-style',
            'transition-duration': '0.16s'
        }},
        { selector: 'node[status="GREEN"]', style: {
            'background-color': '#22c55e', 'border-color': '#16a34a', 'border-width': 3,
            'color': '#ffffff', 'font-weight': '700', 'text-outline-width': 2, 'text-outline-color': '#16a34a'
        }},
        { selector: 'node[status="YELLOW"]', style: {
            'background-color': '#f59e0b', 'border-color': '#d97706', 'border-width': 3,
            'color': '#ffffff', 'font-weight': '700', 'text-outline-width': 2, 'text-outline-color': '#d97706'
        }},
        { selector: 'node[status="RED"]', style: {
            'background-color': '#ef4444', 'border-color': '#dc2626', 'border-width': 3,
            'color': '#ffffff', 'font-weight': '700', 'text-outline-width': 2, 'text-outline-color': '#dc2626'
        }},
        { selector: 'node.collapsed', style: {
            'border-width': '5px', 'border-style': 'double',
            'background-image': 'linear-gradient(135deg, rgba(255,255,255,0.15) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.15) 75%, transparent 75%, transparent)',
            'background-size': '8px 8px',
            'label': function(ele) {
                const lbl  = ele.data('label') || ele.data('hostname') || ele.data('id') || '';
                const h    = ele.data('hiddenCount') || 0;
                const up   = ele.data('upChildren') || 0;
                const down = ele.data('downChildren') || 0;
                if (h === 0) return lbl;
                const statusLine = (up + down > 0) ? `\n${up} up · ${down} down` : '';
                return lbl + '\n▼ ' + h + ' hidden' + statusLine;
            },
            'font-size': '10px', 'font-weight': '600', 'color': '#1e293b',
            'text-valign': 'bottom', 'text-halign': 'center', 'text-margin-y': '5px',
            'text-wrap': 'wrap', 'text-max-width': '110px'
        }},
        { selector: 'node.collapsed[status="GREEN"]', style: {
            'border-color': '#22c55e', 'background-color': '#22c55e'
        }},
        { selector: 'node.collapsed[status="YELLOW"]', style: {
            'border-color': '#f59e0b', 'background-color': '#f59e0b'
        }},
        { selector: 'node.collapsed[status="RED"]', style: {
            'border-color': '#ef4444', 'background-color': '#ef4444'
        }},
        { selector: 'node.shared-node', style: {
            'border-style': 'dashed', 'border-width': '3px', 'border-color': '#8b5cf6'
        }},
        { selector: 'node.hidden-child',    style: { 'display': 'none' }},
        { selector: 'edge.hidden-edge',     style: { 'display': 'none' }},
        { selector: 'node.virtual-root',    style: { 'display': 'none' }},
        { selector: 'node.hovered', style: {
            'border-color': '#2563eb', 'border-width': '4px', 'border-style': 'solid',
            'width': '52px', 'height': '52px', 'shadow-blur': 16, 'shadow-color': 'rgba(37,99,235,.3)'
        }},
        { selector: 'node:selected', style: { 'border-color': '#2563eb', 'border-width': '4px', 'border-style': 'solid' }},
        /* ── edges ── */
        { selector: 'edge[relationship="child"]', style: {
            'curve-style': 'bezier', 'width': 3, 'line-color': '#cbd5e1',
            'target-arrow-shape': 'triangle', 'target-arrow-color': '#cbd5e1',
            'arrow-scale': 0.8, 'label': '', 'overlay-padding': 4, 'opacity': 0.8
        }},
        { selector: 'edge[relationship="child"][status="true"]',  style: { 'line-color': '#22c55e', 'target-arrow-color': '#22c55e', 'width': 3, 'opacity': 1.0 }},
        { selector: 'edge[relationship="child"][status="false"]', style: { 'line-color': '#ef4444', 'target-arrow-color': '#ef4444', 'line-style': 'dashed', 'width': 3, 'opacity': 1.0 }},
        { selector: 'edge[relationship="link"]', style: {
            'curve-style': 'bezier', 'line-style': 'dotted', 'opacity': 0.6, 'width': 2,
            'target-arrow-shape': 'triangle', 'target-arrow-color': '#94a3b8',
            'arrow-scale': 0.6, 'label': '', 'line-color': '#94a3b8'
        }},
        { selector: 'edge[relationship="link"][status="true"]',  style: { 'line-color': '#22c55e', 'target-arrow-color': '#22c55e', 'opacity': 0.8, 'width': 2 }},
        { selector: 'edge[relationship="link"][status="false"]', style: { 'line-color': '#ef4444', 'target-arrow-color': '#ef4444', 'line-style': 'dashed', 'opacity': 0.8, 'width': 2 }},
        { selector: 'edge', style: {
            'curve-style': 'bezier', 'width': 2, 'line-color': '#94a3b8',
            'target-arrow-shape': 'triangle', 'target-arrow-color': '#94a3b8', 'label': ''
        }}
    ];

    /* ═══════════════════════════════════════════════════════════════
       ELEMENTS + VIRTUAL ROOT
    ═══════════════════════════════════════════════════════════════ */
    function findRoots(nodes, edges) {
        const childSet = new Set(edges.filter(e => (e.data.relationship || 'child') === 'child').map(e => e.data.target));
        return nodes.filter(n => !childSet.has(n.data.id));
    }

    function prepareElements(rawData) {
        const nodes = [...(rawData.nodes || [])];
        const edges = [...(rawData.edges || [])];
        const roots = findRoots(nodes, edges);
        console.log('[TOPOLOGY] roots:', roots.map(r => r.data.id));

        let virtualRootId = null;
        if (roots.length > 1) {
            virtualRootId = '__virtual_root__';
            nodes.unshift({ data: { id: virtualRootId, label: '', hostname: '', status: 'GREEN', childCount: roots.length } });
            roots.forEach(r => edges.push({ data: { source: virtualRootId, target: r.data.id, relationship: 'child' } }));
        } else if (roots.length === 0 && nodes.length > 0) {
            virtualRootId = '__virtual_root__';
            nodes.unshift({ data: { id: virtualRootId, label: '', hostname: '', status: 'GREEN', childCount: nodes.length } });
            nodes.slice(1).forEach(n => edges.push({ data: { source: virtualRootId, target: n.data.id, relationship: 'child' } }));
        }

        const hideIds = virtualRootId ? [virtualRootId] : [];
        return {
            nodes: nodes.filter(n => !hideIds.includes(n.data.id)),
            edges: edges.filter(e => !hideIds.includes(e.data.source) && !hideIds.includes(e.data.target)),
            allNodes: nodes, allEdges: edges, virtualRootId
        };
    }

    /* ═══════════════════════════════════════════════════════════════
       TREE FALLBACK POSITIONS
    ═══════════════════════════════════════════════════════════════ */
    function buildTreePositions(nodes, edges) {
        const VGAP = 160, HGAP = 120;
        const children = {}, inDeg = {};
        nodes.forEach(n => { children[n.data.id] = []; inDeg[n.data.id] = 0; });
        edges.filter(e => (e.data.relationship || 'child') === 'child').forEach(e => {
            const s = e.data.source, t = e.data.target;
            if (children[s] && !children[s].includes(t)) children[s].push(t);
            if (t in inDeg) inDeg[t] = (inDeg[t] || 0) + 1;
        });
        const roots = nodes.filter(n => inDeg[n.data.id] === 0);
        if (!roots.length) return {};
        const subtreeLeaves = (id, seen = new Set()) => {
            if (seen.has(id)) return 1; seen.add(id);
            const ch = children[id] || [];
            return ch.length ? ch.reduce((s, c) => s + subtreeLeaves(c, seen), 0) : 1;
        };
        const pos = {}, placed = new Set();
        const place = (id, cx, depth, seen = new Set()) => {
            if (seen.has(id) || placed.has(id)) return; seen.add(id); placed.add(id);
            pos[id] = { x: cx, y: depth * VGAP + 80 };
            const ch = (children[id] || []).filter(c => !seen.has(c) && !placed.has(c));
            if (!ch.length) return;
            const total = ch.reduce((s, c) => s + subtreeLeaves(c), 0);
            let ox = cx - ((total - 1) / 2) * HGAP;
            ch.forEach(c => { const lv = subtreeLeaves(c); place(c, ox + ((lv - 1) / 2) * HGAP, depth + 1, seen); ox += lv * HGAP; });
        };
        let offset = 0;
        roots.forEach(r => { place(r.data.id, offset + (subtreeLeaves(r.data.id) * HGAP) / 2, 0); offset = Math.max(...Object.values(pos).map(p => p.x)) + HGAP * 3; });
        nodes.forEach(n => { if (!placed.has(n.data.id)) { pos[n.data.id] = { x: offset, y: 80 }; offset += HGAP; placed.add(n.data.id); } });
        return pos;
    }

    /* ═══════════════════════════════════════════════════════════════
       HIERARCHY MAPS
    ═══════════════════════════════════════════════════════════════ */
    function buildHierarchyMaps() {
        childrenMap.clear(); parentMap.clear();
        cy.nodes().forEach(n => { childrenMap.set(n.id(), new Set()); parentMap.set(n.id(), new Set()); });
        cy.edges().filter(e => (e.data('relationship') || 'child') === 'child').forEach(e => {
            const src = e.data('source'), tgt = e.data('target');
            if (childrenMap.has(src)) childrenMap.get(src).add(tgt);
            if (parentMap.has(tgt)) parentMap.get(tgt).add(src);
        });
    }

    function directChildIds(nodeId) { return childrenMap.get(nodeId) || new Set(); }
    function getParentIds(nodeId)   { return parentMap.get(nodeId)   || new Set(); }

    /* ═══════════════════════════════════════════════════════════════
       STATUS PROPAGATION
       Only overwrites VIRTUAL / AGGREGATION (parent) nodes.
       Leaf/device nodes keep the status computed server-side by
       derive_node_status() and are never touched here.
    ═══════════════════════════════════════════════════════════════ */
    function computeAggregationStatus() {
        const visited = new Set();
        function calc(nodeId) {
            if (visited.has(nodeId)) { const n = cy.getElementById(nodeId); return n.length ? n.data('status') : 'GREEN'; }
            visited.add(nodeId);
            const children = [...directChildIds(nodeId)];
            if (!children.length) { const n = cy.getElementById(nodeId); return n.length ? n.data('status') : 'GREEN'; }
            let green = 0, red = 0;
            children.forEach(cid => { const s = calc(cid); if (s === 'GREEN') green++; else red++; });
            const status = green === children.length ? 'GREEN' : red === children.length ? 'RED' : 'YELLOW';
            const node = cy.getElementById(nodeId);
            if (node.length) { node.data('status', status); node.data('upChildren', green); node.data('downChildren', red); }
            return status;
        }
        cy.nodes().forEach(n => calc(n.id()));
    }

    function updateParentStatus(nodeId) {
        const ancestors = new Set();
        function walkUp(nid) { ancestors.add(nid); for (const pid of getParentIds(nid)) { if (!ancestors.has(pid)) walkUp(pid); } }
        walkUp(nodeId);
        const visited = new Set();
        function calc(nid) {
            if (visited.has(nid)) { const n = cy.getElementById(nid); return n.length ? n.data('status') : 'GREEN'; }
            visited.add(nid);
            const children = [...directChildIds(nid)];
            if (!children.length) { const n = cy.getElementById(nid); return n.length ? n.data('status') : 'GREEN'; }
            let green = 0, red = 0;
            children.forEach(cid => { const s = calc(cid); if (s === 'GREEN') green++; else red++; });
            const status = green === children.length ? 'GREEN' : red === children.length ? 'RED' : 'YELLOW';
            const node = cy.getElementById(nid);
            if (node.length) { node.data('status', status); node.data('upChildren', green); node.data('downChildren', red); }
            return status;
        }
        ancestors.forEach(nid => calc(nid));
    }

    /* ═══════════════════════════════════════════════════════════════
       COLLAPSE / EXPAND
    ═══════════════════════════════════════════════════════════════ */
    function shouldHide(nodeId, collapsingRoot) {
        const parents = getParentIds(nodeId);
        if (parents.size === 0) return false;
        for (const pid of parents) {
            if (pid !== collapsingRoot && !collapsedNodes.has(pid)) {
                const pNode = cy.nodes(`[id="${pid}"]`);
                if (pNode.length && !pNode.hasClass('hidden-child')) return false;
            }
        }
        return true;
    }

    function getVisibleDescendants(nodeId) {
        const result = [], visited = new Set(), queue = [nodeId];
        visited.add(nodeId);
        while (queue.length) {
            const cur = queue.shift();
            for (const cid of directChildIds(cur)) {
                if (visited.has(cid)) continue;
                visited.add(cid);
                if (shouldHide(cid, nodeId)) { result.push(cid); queue.push(cid); }
            }
        }
        return result;
    }

    function hideDescendants(nodeId) {
        getVisibleDescendants(nodeId).forEach(cid => {
            const child = cy.nodes(`[id="${cid}"]`);
            if (!child.length) return;
            if (collapsedNodes.has(cid) || child.hasClass('hidden-child')) {
                cy.edges(`[source="${nodeId}"][target="${cid}"]`).addClass('hidden-edge');
                cy.edges(`[source="${cid}"][target="${nodeId}"]`).addClass('hidden-edge');
                return;
            }
            child.addClass('hidden-child');
            cy.edges().filter(e => e.data('source') === cid || e.data('target') === cid).forEach(e => e.addClass('hidden-edge'));
        });
    }

    function showDirectChildren(nodeId, visited) {
        if (!visited) visited = new Set();
        for (const cid of directChildIds(nodeId)) {
            if (visited.has(cid)) continue;
            visited.add(cid);
            const child = cy.nodes(`[id="${cid}"]`);
            if (!child.length) continue;
            child.removeClass('hidden-child collapsed-child');
            cy.edges(`[source="${nodeId}"][target="${cid}"]`).removeClass('hidden-edge');
            cy.edges(`[source="${cid}"][target="${nodeId}"]`).removeClass('hidden-edge');
            cy.edges().filter(e => e.data('source') === cid || e.data('target') === cid).forEach(e => {
                const otherId = e.data('source') === cid ? e.data('target') : e.data('source');
                const other = cy.nodes(`[id="${otherId}"]`);
                if (other.length && !other.hasClass('hidden-child')) e.removeClass('hidden-edge');
            });
            if (collapsedNodes.has(cid)) child.addClass('collapsed');
            else showDirectChildren(cid, visited);
        }
    }

    function collapseNode(nodeId) {
        const node = cy.nodes(`[id="${nodeId}"]`);
        if (!node.length) return;
        collapsedNodes.add(nodeId);
        node.data('hiddenCount', getVisibleDescendants(nodeId).length);
        node.addClass('collapsed');
        hideDescendants(nodeId);
    }

    function expandNode(nodeId) {
        const node = cy.nodes(`[id="${nodeId}"]`);
        if (!node.length) return;
        collapsedNodes.delete(nodeId);
        node.data('hiddenCount', 0);
        node.removeClass('collapsed');
        showDirectChildren(nodeId);
    }

    function collapseAll() {
        cy.nodes().forEach(n => { if (n.data('hasChildren')) collapseNode(n.id()); });
        cy.animate({ fit: { eles: cy.elements(':visible'), padding: 40 } }, { duration: 350 });
        scheduleSave();
    }

    function expandAll() {
        cy.nodes().forEach(n => { collapsedNodes.delete(n.id()); n.removeClass('collapsed hidden-child collapsed-child'); n.data('hiddenCount', 0); });
        cy.edges().forEach(e => e.removeClass('hidden-edge'));
        cy.animate({ fit: { eles: cy.elements(':visible'), padding: 40 } }, { duration: 350 });
        scheduleSave();
    }

    /* ═══════════════════════════════════════════════════════════════
       DEPTH / TAG
    ═══════════════════════════════════════════════════════════════ */
    function computeDepthMap() {
        depthMap = {};
        const roots = [], visited = new Set(), queue = [];
        parentMap.forEach((parents, nid) => { if (parents.size === 0) roots.push(nid); });
        roots.forEach(r => { depthMap[r] = 0; queue.push(r); visited.add(r); });
        while (queue.length) {
            const cid = queue.shift();
            for (const childId of directChildIds(cid)) {
                if (!visited.has(childId)) { visited.add(childId); depthMap[childId] = depthMap[cid] + 1; queue.push(childId); }
            }
        }
        cy.nodes().forEach(n => { if (!(n.id() in depthMap)) depthMap[n.id()] = 0; });
    }

    function computeChildCountMap() {
        childCountMap = {};
        childrenMap.forEach((ids, nid) => { childCountMap[nid] = ids.size; });
    }

    function tagParentNodes() {
        computeChildCountMap();
        cy.nodes().forEach(node => {
            const count  = childCountMap[node.id()] || 0;
            const pCount = parentMap.has(node.id()) ? parentMap.get(node.id()).size : 0;
            node.data('hasChildren', count > 0);
            node.data('childCount', count);
            node.data('parentCount', pCount);
        });
    }

    function autoHideDeep() {
        computeChildCountMap();
        const w = window.innerWidth;
        const maxAutoDepth = w <= 576 ? 2 : w <= 992 ? 3 : 3;
        cy.nodes().forEach(node => {
            const depth = depthMap ? (depthMap[node.id()] || 0) : 0;
            if (depth >= maxAutoDepth && (childCountMap[node.id()] || 0) >= 2 && !collapsedNodes.has(node.id())) collapseNode(node.id());
        });
    }

    /* ═══════════════════════════════════════════════════════════════
       SMART COLLAPSE — depth / threshold / category / problems
    ═══════════════════════════════════════════════════════════════ */
    function hideCategory(category) {
        hiddenCategories.add(category);
        cy.nodes().forEach(node => {
            if (node.data('category') === category && !node.data('hasChildren')) {
                node.addClass('hidden-child');
                node.connectedEdges().forEach(e => e.addClass('hidden-edge'));
            }
        });
        scheduleSave();
    }

    function showCategory(category) {
        hiddenCategories.delete(category);
        cy.nodes().forEach(node => {
            if (node.data('category') === category) {
                node.removeClass('hidden-child');
                node.connectedEdges().forEach(e => {
                    const otherId = e.data('source') === node.id() ? e.data('target') : e.data('source');
                    const other = cy.nodes(`[id="${otherId}"]`);
                    if (other.length && !other.hasClass('hidden-child')) e.removeClass('hidden-edge');
                });
            }
        });
        scheduleSave();
    }

    function showAllCategories() {
        hiddenCategories.clear();
        cy.nodes().forEach(node => node.removeClass('hidden-child'));
        cy.edges().forEach(e => e.removeClass('hidden-edge'));
        /* Re-apply collapse state */
        collapsedNodes.forEach(nid => {
            const node = cy.nodes(`[id="${nid}"]`);
            if (node.length) { node.addClass('collapsed'); hideDescendants(nid); }
        });
        scheduleSave();
    }

    function detectSharedNodes() {
        cy.nodes().forEach(node => {
            if ((node.data('parentCount') || 0) > 1) {
                node.addClass('shared-node');
            }
        });
    }

    /* ═══════════════════════════════════════════════════════════════
       PERSIST STATE
    ═══════════════════════════════════════════════════════════════ */
    async function loadDashboardState() {
        try { const r = await fetch('/api/dashboard-state'); if (!r.ok) return null; return await r.json(); } catch { return null; }
    }

    function scheduleSave() {
        if (suppressSave || !window.IS_ADMIN) return;
        clearTimeout(saveTimer);
        saveTimer = setTimeout(persistState, 1200);
    }

    async function persistState() {
        if (!cy) return;
        const pan = cy.pan(), positions = {};
        cy.nodes().forEach(n => { const p = n.position(); positions[n.id()] = { x: p.x, y: p.y }; });
        try {
            await fetch('/api/dashboard-state', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
                body: JSON.stringify({ zoom: cy.zoom(), pan_x: pan.x, pan_y: pan.y, collapsed: Array.from(collapsedNodes), node_positions: positions, layout_locked: layoutLocked, hidden_categories: Array.from(hiddenCategories) })
            });
            flashSyncBadge();
        } catch {}
    }

    function flashSyncBadge() {
        const b = el.syncBadge;
        if (!b) return;
        b.classList.add('show');
        setTimeout(() => b.classList.remove('show'), 2200);
    }

    /* ═══════════════════════════════════════════════════════════════
       LOCK
    ═══════════════════════════════════════════════════════════════ */
    function applyLockState() {
        if (!window.IS_ADMIN) return;
        const btn = el.lockLayoutBtn;
        if (!btn) return;
        if (layoutLocked) {
            cy.nodes().ungrabify();
            btn.innerHTML = '<i class="fas fa-lock"></i> Locked';
            if (cfg.mode === 'fullscreen') btn.classList.add('active-lock');
            else { btn.classList.remove('btn-outline-secondary'); btn.classList.add('btn-outline-danger'); }
        } else {
            cy.nodes().grabify();
            btn.innerHTML = '<i class="fas fa-lock-open"></i> Unlocked';
            if (cfg.mode === 'fullscreen') btn.classList.remove('active-lock');
            else { btn.classList.remove('btn-outline-danger'); btn.classList.add('btn-outline-secondary'); }
        }
    }

    /* ═══════════════════════════════════════════════════════════════
       PING FLASH
    ═══════════════════════════════════════════════════════════════ */
    function showPingFlash(msg) {
        const e = el.pingFlash;
        if (!e) return;
        e.innerHTML = msg; e.style.display = 'block';
        setTimeout(() => { e.style.display = 'none'; }, 6000);
    }

    /* ═══════════════════════════════════════════════════════════════
       KPI UPDATE
    ═══════════════════════════════════════════════════════════════ */
    function updateKpi(data) {
        const set = (e, v) => { if (e) e.textContent = v; };
        set(el.kpiTotal, data.total || 0);
        set(el.kpiUp,    data.up    || 0);
        set(el.kpiDown,  data.down  || 0);
        if (el.kpiAlerts)    set(el.kpiAlerts,    data.down || 0);
        if (el.downDevices)  set(el.downDevices,  data.down || 0);
        if (el.categoryContainer) {
            catCarouselData = (data.categories || []).filter(c => c.total);
            const cc = el.categoryCount;
            if (cc) cc.textContent = catCarouselData.length + ' Types';
            renderCatMarquee();
        }
    }

    /* ═══════════════════════════════════════════════════════════════
       RESPONSIVE: breakpoint detection & debounced resize
    ═══════════════════════════════════════════════════════════════ */
    function getBreakpoint() {
        const w = window.innerWidth;
        if (w <= 576) return 'xs';
        if (w <= 768) return 'sm';
        if (w <= 992) return 'md';
        if (w <= 1200) return 'lg';
        return 'xl';
    }

    let lastBreakpoint = getBreakpoint();
    let resizeTimer = null;

    function onResize() {
        const bp = getBreakpoint();
        if (bp !== lastBreakpoint) {
            lastBreakpoint = bp;
            if (cy) {
                cy.resize();
                cy.fit(40);
                autoHideDeep();
            }
        } else if (cy) {
            cy.resize();
            cy.fit(40);
        }
    }

    window.addEventListener('resize', function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(onResize, 250);
    });

    /* ═══════════════════════════════════════════════════════════════
       INIT GRAPH
    ═══════════════════════════════════════════════════════════════ */
    async function initGraph(rawData, savedState) {
        const cyEl   = el.cy;
        const loadEl = el.loading;
        if (loadEl) loadEl.style.display = 'none';
        if (cyEl)   cyEl.style.display   = 'block';
        if (cy) { cy.destroy(); cy = null; }

        depthMap = null; childCountMap = null;

        const prep    = prepareElements(rawData);
        const treePos = buildTreePositions(prep.allNodes, prep.allEdges);

        cy = cytoscape({
            container: cyEl,
            style: CY_STYLE,
            minZoom: 0.1, maxZoom: 5,
            boxSelectionEnabled: false,
            layout: { name: 'preset' },
            elements: {
                nodes: prep.allNodes.map(n => ({
                    data: n.data,
                    position: treePos[n.data.id] || { x: 400, y: 300 },
                    classes: n.data.id === prep.virtualRootId ? 'virtual-root' : ''
                })),
                edges: prep.allEdges.map(e => ({
                    data: { ...e.data, status: String(e.data.status === true || e.data.status === 'true'), relationship: e.data.relationship || 'child' }
                }))
            }
        });

        tagParentNodes();
        buildHierarchyMaps();
        computeAggregationStatus();
        computeDepthMap();
        detectSharedNodes();

        /* RBAC: disable node dragging for viewers */
        if (!window.IS_ADMIN) {
            cy.autoungrabify(true);
        }

        if (savedState && savedState.collapsed && savedState.collapsed.length) {
            savedState.collapsed.forEach(nid => collapseNode(nid));
        } else {
            autoHideDeep();
        }

        /* Restore hidden categories */
        if (savedState && savedState.hidden_categories && savedState.hidden_categories.length) {
            savedState.hidden_categories.forEach(cat => {
                hiddenCategories.add(cat);
                cy.nodes().forEach(node => {
                    if (node.data('category') === cat && !node.data('hasChildren')) {
                        node.addClass('hidden-child');
                        node.connectedEdges().forEach(e => e.addClass('hidden-edge'));
                    }
                });
            });
        }

        if (savedState && savedState.layout_locked) {
            const savedPos = savedState.node_positions || {};
            if (Object.keys(savedPos).length) cy.nodes().forEach(n => { if (savedPos[n.id()]) n.position(savedPos[n.id()]); });
            layoutLocked = true;
            applyLockState();
            if (typeof savedState.zoom === 'number' && savedState.zoom > 0) {
                cy.zoom(savedState.zoom);
                cy.pan({ x: savedState.pan_x || 0, y: savedState.pan_y || 0 });
            } else { cy.fit(40); cy.center(); }
        } else {
            await runELK();
        }

        persistState();
        const lb = el.legendBox;
        if (lb) lb.style.display = 'block';
        setupCyEvents(cyEl);
        initMinimap();
    }

    /* ── ELK + Dagre fallback ── */
    async function runELK(animate = false) {
        const w = window.innerWidth;
        const nodeSpacing = w <= 576 ? '50' : w <= 992 ? '65' : '80';
        const layerSpacing = w <= 576 ? '100' : w <= 992 ? '130' : '160';
        try {
            await new Promise((resolve, reject) => {
                cy.one('layoutstop', resolve);
                cy.one('layouterror', reject);
                cy.layout({
                    name: 'elk',
                    elk: {
                        'elk.algorithm': 'layered',
                        'elk.direction': 'DOWN',
                        'elk.spacing.nodeNode': nodeSpacing,
                        'elk.layered.spacing.nodeNodeBetweenLayers': layerSpacing,
                        'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
                        'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
                        'elk.layered.considerModelOrder.strategy': 'NODES_AND_EDGES',
                        'elk.layered.nodePlacement.bk.fixedAlignment': 'BALANCED'
                    },
                    fit: true, padding: w <= 576 ? 20 : 50,
                    animate, animationDuration: 500
                }).run();
            });
            console.log('[TOPOLOGY] ELK layout done');
        } catch (err) {
            console.error('[TOPOLOGY] ELK failed, trying Dagre', err);
            try {
                await new Promise((resolve, reject) => {
                    cy.one('layoutstop', resolve);
                    cy.one('layouterror', reject);
                    cy.layout({ name: 'dagre', rankDir: 'TB', rankSep: 150, nodeSep: 100, fit: true, animate, animationDuration: 500, padding: 50 }).run();
                });
                console.log('[TOPOLOGY] Dagre fallback done');
            } catch (err2) {
                console.error('[TOPOLOGY] Dagre also failed', err2);
                cy.fit(40); cy.center();
            }
        }
    }

    /* ── Minimap ── */
    function initMinimap() {
        if (!cy || navInstance) return;
        const minimapEl = el.minimap;
        if (!minimapEl || typeof cy.navigator !== 'function') return;
        const isDark = cfg.mode === 'fullscreen';
        navInstance = cy.navigator({
            container: minimapEl,
            viewLiveFramerate: 0, thumbnailLiveFramerate: -1, thumbnailPanFadeTime: 0,
            dblClickDelay: 300, showEdgeLabels: false,
            style: {
                colors: {
                    bg:            isDark ? '#1e293b' : '#f8fafd',
                    node:          '#3b82f6', nodeOutline: '#2563eb',
                    parent:        'rgba(59,130,246,.12)', parentOutline: '#2563eb',
                    edge:          isDark ? '#475569' : '#94a3b8',
                    edgeOutline:   isDark ? '#334155' : '#64748b',
                    overlay:       'rgba(59,130,246,.08)', overlayOutline: 'rgba(59,130,246,.25)'
                },
                size: [180, 120]
            }
        });
        minimapEl.style.display = 'block';
    }

    /* ═══════════════════════════════════════════════════════════════
       CYTOSCAPE EVENTS
    ═══════════════════════════════════════════════════════════════ */
    function setupCyEvents(cyEl) {
        cy.on('mouseover', 'node', evt => { evt.target.addClass('hovered'); renderTooltip(evt.target); positionTooltip(evt); });
        cy.on('mouseout',  'node', evt => { evt.target.removeClass('hovered'); const tt = el.nodeTooltip; if (tt) tt.style.display = 'none'; });
        cy.on('mousemove', 'node', positionTooltip);
        cy.on('tap', 'node', evt => {
            updateSiteInfoPanel(evt.target.data());
            cy.animate({ center: { eles: evt.target }, zoom: 1.4 }, { duration: 300 });
        });
        cy.on('tap', 'edge', evt => openEdgeModal(evt.target.data()));

        cyEl.addEventListener('dblclick', e => {
            const pt  = cy.renderer().projectIntoViewport(e.clientX, e.clientY);
            const hit = cy.nodes().filter(n => { const bb = n.boundingBox(); return pt[0] >= bb.x1 && pt[0] <= bb.x2 && pt[1] >= bb.y1 && pt[1] <= bb.y2; });
            const node = hit[0];
            if (!node || !node.data('hasChildren')) return;
            const nid = node.id();
            if (collapsedNodes.has(nid)) expandNode(nid); else collapseNode(nid);
            cy.animate({ fit: { eles: cy.elements(':visible'), padding: 40 } }, { duration: 380 });
            scheduleSave();
        });

        cyEl.addEventListener('contextmenu', e => {
            e.preventDefault();
            const pt  = cy.renderer().projectIntoViewport(e.clientX, e.clientY);
            const hit = cy.nodes().filter(n => { const bb = n.boundingBox(); return pt[0] >= bb.x1 && pt[0] <= bb.x2 && pt[1] >= bb.y1 && pt[1] <= bb.y2; });
            const node = hit[0];
            if (!node) return;
            ctxNode = node;
            openCtxMenu(e.clientX, e.clientY);
        });

        cy.on('dragfree', 'node', () => scheduleSave());
        cy.on('viewport',          () => { const tt = el.nodeTooltip; if (tt) tt.style.display = 'none'; scheduleSave(); });
        cy.on('layoutstop',        () => scheduleSave());
    }

    /* ═══════════════════════════════════════════════════════════════
       TOOLTIP
    ═══════════════════════════════════════════════════════════════ */
    function renderTooltip(node) {
        const d    = node.data();
        const isUp = d.status === 'GREEN', isY = d.status === 'YELLOW';
        const col  = isUp ? '#4ade80' : (isY ? '#fcd34d' : '#f87171');
        const ico  = isUp ? 'fa-circle-check' : (isY ? 'fa-circle-exclamation' : 'fa-circle-xmark');
        const stat = isUp ? 'ONLINE' : (isY ? 'PARTIAL' : 'OFFLINE');
        const childRow = d.hasChildren
            ? `<div class="tt-children"><i class="fas fa-sitemap"></i>${d.childCount} child${d.childCount > 1 ? 'ren' : ''} · dbl-click to ${collapsedNodes.has(d.id) ? 'expand' : 'collapse'}</div>`
            : '';
        const tt = el.nodeTooltip;
        if (!tt) return;
        tt.innerHTML =
            `<div class="tt-title"><i class="fas fa-server" style="color:#93c5fd;font-size:13px;"></i>${d.hostname || d.device_name || d.id}</div>` +
            `<div class="tt-divider"></div>` +
            `<div class="tt-row"><span class="tt-label">IP Address</span><span class="tt-value">${d.id}</span></div>` +
            (d.device_name && d.hostname && d.device_name !== d.hostname ? `<div class="tt-row"><span class="tt-label">Device name</span><span class="tt-value">${d.device_name}</span></div>` : '') +
            `<div class="tt-row"><span class="tt-label">Location</span><span class="tt-value">${d.location || '—'}</span></div>` +
            `<div class="tt-row"><span class="tt-label">Category</span><span class="tt-value">${d.category || '—'}</span></div>` +
            `<div class="tt-row"><span class="tt-label">Model</span><span class="tt-value">${d.model || '—'}</span></div>` +
            `<div class="tt-row"><span class="tt-label">Status</span><span class="tt-status" style="color:${col}"><i class="fas ${ico}"></i>${stat}</span></div>` +
            childRow +
            `<div class="tt-hint"><i class="fas fa-mouse me-1"></i>Dbl-click expand · Right-click options</div>`;
        tt.style.display = 'block';
    }

    function positionTooltip(evt) {
        const tt = el.nodeTooltip;
        if (!tt) return;
        const rect = cy.container().getBoundingClientRect();
        const r    = evt.target.renderedPosition();
        let left = rect.left + r.x + 24, top = rect.top + r.y - 18;
        if (left + 295 > window.innerWidth)  left = rect.left + r.x - 305;
        if (top  + 220 > window.innerHeight) top  = window.innerHeight - 230;
        if (top < 6) top = 6;
        tt.style.left = left + 'px'; tt.style.top = top + 'px';
    }

    /* ═══════════════════════════════════════════════════════════════
       SITE INFO / ALERT PANEL (mode-aware)
    ═══════════════════════════════════════════════════════════════ */
    function updateSiteInfoPanel(d) {
        const isUp = d.status === 'GREEN', isY = d.status === 'YELLOW';

        if (cfg.mode === 'fullscreen') {
            const panel = el.alertPanel;
            if (!panel) return;
            const bc = isUp ? '#22c55e' : (isY ? '#f59e0b' : '#ef4444');
            const lb = isUp ? 'ONLINE'  : (isY ? 'PARTIAL'  : 'OFFLINE');
            panel.classList.add('show');
            panel.innerHTML =
                `<div class="alert-head"><span><i class="fas fa-server me-1"></i>${d.hostname || d.device_name || d.id}</span><span style="color:${bc};">${lb}</span></div>` +
                `<div style="font-size:11px;color:#94a3b8;"><i class="fas fa-map-marker-alt me-1"></i>${d.location || 'Unknown'} <i class="fas fa-tag ms-2 me-1"></i>${d.category || 'device'}</div>` +
                (d.hasChildren ? `<div style="font-size:11px;color:#3b82f6;margin-top:4px;"><i class="fas fa-sitemap me-1"></i>${d.childCount} children (${collapsedNodes.has(d.id) ? 'collapsed' : 'expanded'})</div>` : '');
            setTimeout(() => panel.classList.remove('show'), 5000);
        } else {
            const panel = el.siteInfoPanel;
            if (!panel) return;
            const bc = isUp ? 'badge-soft-success' : (isY ? 'badge-soft-warning' : 'badge-soft-danger');
            const lb = isUp ? 'ONLINE' : (isY ? 'PARTIAL' : 'OFFLINE');
            const hint = d.hasChildren
                ? `<span style="font-size:10px;color:#3b82f6;margin-left:6px;"><i class="fas fa-sitemap"></i> ${d.childCount} children (${collapsedNodes.has(d.id) ? 'collapsed' : 'expanded'} · dbl-click)</span>`
                : '';
            panel.innerHTML =
                `<div style="display:flex;justify-content:space-between;align-items:center;">
                    <div><i class="fas fa-server me-1 text-primary"></i><strong style="font-size:12px;">${d.hostname || d.device_name || d.id}</strong>${hint}
                    <div style="font-size:9px;color:#5f7f9e;margin-top:1px;">${d.id || '—'}</div></div>
                    <span class="${bc}">${lb}</span>
                </div>
                <div style="margin-top:5px;color:#475569;font-size:11px;">
                    <i class="fas fa-map-marker-alt me-1 text-muted"></i>${d.location || 'Unknown'}
                    &nbsp;<i class="fas fa-tag ms-2 text-muted"></i>${d.category || 'device'}
                </div>`;
        }
    }

    /* ═══════════════════════════════════════════════════════════════
       EDGE MODAL
    ═══════════════════════════════════════════════════════════════ */
    function openEdgeModal(d) {
        const title = el.modalTitle, body = el.modalBody;
        if (!title || !body) return;
        const up = d.status === true || d.status === 'true';
        const isDark = cfg.mode === 'fullscreen';
        title.innerHTML = `<i class="fas fa-exchange-alt me-2" style="color:#3b82f6;"></i>${d.source} ↔ ${d.target}`;
        body.innerHTML =
            `<div style="background:${up ? (isDark ? 'rgba(34,197,94,.15)' : '#dcfce7') : (isDark ? 'rgba(239,68,68,.15)' : '#fee2e2')};color:${up ? (isDark ? '#4ade80' : '#166534') : (isDark ? '#f87171' : '#991b1b')};text-align:center;padding:10px;border-radius:10px;font-weight:700;margin-bottom:14px;font-size:14px;">
                <i class="fas ${up ? 'fa-circle-check' : 'fa-circle-xmark'} me-2"></i>${up ? 'LINK IS UP' : 'LINK IS DOWN'}
            </div>
            <table style="width:100%;font-size:13px;border-collapse:collapse;">
                <tr><th style="width:35%;color:${isDark ? '#94a3b8' : '#64748b'};text-align:left;padding:4px 0;">Source</th><td style="color:${isDark ? '#e2e8f0' : 'inherit'};"><strong>${d.source}</strong> <span style="color:#64748b;">${d.source_location || ''}</span></td></tr>
                <tr><th style="color:${isDark ? '#94a3b8' : '#64748b'};text-align:left;padding:4px 0;">Target</th><td style="color:${isDark ? '#e2e8f0' : 'inherit'};"><strong>${d.target}</strong> <span style="color:#64748b;">${d.destination_location || ''}</span></td></tr>
                <tr><th style="color:${isDark ? '#94a3b8' : '#64748b'};text-align:left;padding:4px 0;">Remark</th><td style="color:${isDark ? '#e2e8f0' : 'inherit'};">${d.label || '—'}</td></tr>
                <tr><th style="color:${isDark ? '#94a3b8' : '#64748b'};text-align:left;padding:4px 0;">Latency</th><td style="color:${isDark ? '#e2e8f0' : 'inherit'};">${d.latency_ms != null ? d.latency_ms + ' ms' : '—'}</td></tr>
                <tr><th style="color:${isDark ? '#94a3b8' : '#64748b'};text-align:left;padding:4px 0;">Last Check</th><td style="color:${isDark ? '#e2e8f0' : 'inherit'};">${d.last_checked || '—'}</td></tr>
            </table>`;
        showModal();
    }

    function showModal() { const o = el.modalOverlay; if (o) o.classList.add('show'); }
    function hideModal() { const o = el.modalOverlay; if (o) o.classList.remove('show'); }

    /* ═══════════════════════════════════════════════════════════════
       CONTEXT MENU
    ═══════════════════════════════════════════════════════════════ */
    function openCtxMenu(clientX, clientY) {
        const menu = el.ctxMenu;
        if (!menu) return;
        const nid = ctxNode.id(), d = ctxNode.data();
        const isCollapsed = collapsedNodes.has(nid);

        const upCh = d.upChildren || 0, downCh = d.downChildren || 0;
        let statusLine = '';
        if (upCh + downCh > 0) {
            const sc = d.status === 'GREEN' ? '#22c55e' : d.status === 'RED' ? '#ef4444' : '#f59e0b';
            statusLine = `<br><span style="font-size:11px;color:${sc};">${upCh > 0 ? upCh + ' up' : ''}${upCh > 0 && downCh > 0 ? ' · ' : ''}${downCh > 0 ? downCh + ' down' : ''}</span>`;
        }
        menu.querySelector('#ctxIpHeader').innerHTML =
            `<strong>${d.hostname || d.device_name || nid}</strong>` +
            (d.tooltip && d.tooltip !== nid ? `<br><span style="font-size:11px;color:#94a3b8;">${d.tooltip}</span>` : '') +
            statusLine +
            (d.hiddenCount > 0 ? `<br><span style="font-size:11px;color:#f59e0b;">${d.hiddenCount} hidden</span>` : '');

        menu.querySelector('#ctxExpand').style.display       = isCollapsed ? 'flex' : 'none';
        menu.querySelector('#ctxCollapseNode').style.display = (!isCollapsed && d.hasChildren) ? 'flex' : 'none';

        menu.style.display = 'block';
        const mw = menu.offsetWidth || 205, mh = menu.offsetHeight || 240;
        menu.style.left = (clientX + mw > window.innerWidth  ? clientX - mw : clientX) + 'px';
        menu.style.top  = (clientY + mh > window.innerHeight ? clientY - mh : clientY) + 'px';
    }

    function closeCtxMenu() { const m = el.ctxMenu; if (m) m.style.display = 'none'; }

    /* ═══════════════════════════════════════════════════════════════
       ALERTS + CATEGORY MARQUEE (dashboard only)
    ═══════════════════════════════════════════════════════════════ */
    function startAlertTicker() {
        stopAlertTicker();
        alertInterval = setInterval(() => {
            if (alertPaused) return;
            const panel = el.alertList;
            if (!panel) return;
            const first = panel.firstElementChild;
            if (!first || first.classList.contains('text-muted')) return;
            first.style.marginTop = `-${ALERT_HEIGHT}px`;
            first.style.opacity = '0';
            setTimeout(() => { first.style.marginTop = ''; first.style.opacity = ''; panel.appendChild(first); }, 400);
        }, 2500);
    }
    function stopAlertTicker() { if (alertInterval) { clearInterval(alertInterval); alertInterval = null; } }

    function renderCatMarquee() {
        const e = el.categoryContainer;
        if (!e || !catCarouselData.length) { if (e) e.innerHTML = ''; return; }
        const cards = catCarouselData.map(c => {
            const t = c.total || 1, u = c.up || 0, d = c.down || 0;
            const pct = Math.round((u / t) * 100);
            const cls = pct >= 80 ? '' : pct >= 50 ? ' degraded' : ' critical';
            return `<div class="category-tile">
                <div class="cat-title">${c.category || 'other'}</div>
                <div class="cat-total-devices">${t}</div>
                <div class="cat-progress"><div class="cat-progress-fill${cls}" style="width:${pct}%"></div></div>
                <div class="cat-stats"><span class="up"><i class="fas fa-arrow-up"></i> ${u}</span><span class="down"><i class="fas fa-arrow-down"></i> ${d}</span></div>
            </div>`;
        }).join('');
        e.innerHTML = cards + cards;
    }

    /* ═══════════════════════════════════════════════════════════════
       DATA LOADERS
    ═══════════════════════════════════════════════════════════════ */
    async function loadGraph() {
        try {
            const [topo, state] = await Promise.all([
                fetch('/api/topology').then(r => r.json()),
                loadDashboardState()
            ]);
            await initGraph(topo, state);
        } catch (ex) { console.error('loadGraph:', ex); }
    }

    async function loadAlerts() {
        try {
            const alerts = await fetch('/api/alerts').then(r => r.json());
            const count  = alerts.length;
            const ac = el.alertCount; if (ac) ac.textContent = count;
            const aa = el.activeAlerts; if (aa) aa.textContent = count;

            if (cfg.mode === 'fullscreen') {
                /* fullscreen: simple list in alert panel */
                const list = el.alertList;
                if (!list) return;
                list.innerHTML = count
                    ? alerts.map(a => `<div class="alert-item"><i class="fas fa-bell me-1"></i><strong>${a.label}</strong><br><span style="color:#94a3b8;">${a.ip}${a.location ? ' · ' + a.location : ''}</span></div>`).join('')
                    : '<div style="color:#64748b;padding:4px;"><i class="fas fa-check-circle" style="color:#22c55e;"></i> No active alerts</div>';
            } else {
                /* dashboard: ticker */
                const list = el.alertList;
                if (!list) return;
                if (count) {
                    list.innerHTML = alerts.map(a => `<div class="alert-item"><i class="fas fa-bell me-1"></i><strong>${a.label}</strong><br><span style="color:#64748b;">${a.ip}${a.location ? ' · ' + a.location : ''}</span></div>`).join('');
                    startAlertTicker();
                } else {
                    stopAlertTicker();
                    list.innerHTML = '<div class="text-muted px-2 py-1"><i class="fas fa-check-circle text-success me-1"></i>No active alerts</div>';
                }
            }
        } catch {}
    }

    async function loadDevices() {
        try {
            const data = await fetch('/api/devices-stats').then(r => r.json());
            updateKpi(data);
        } catch {}
    }

    function updateLastPoll() {
        const e = el.lastPoll;
        if (!e) return;
        e.textContent = new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    /* ═══════════════════════════════════════════════════════════════
       ANIMATIONS
    ═══════════════════════════════════════════════════════════════ */
    function animateRecovery(node) {
        node.animate({ style: { width: '52px', height: '52px' } }, { duration: 300 });
        setTimeout(() => node.animate({ style: { width: '42px', height: '42px' } }, { duration: 300 }), 300);
    }
    function animateFailure(node) {
        const pos = node.position();
        node.animate({ position: { x: pos.x + 8, y: pos.y } }, { duration: 80 });
        setTimeout(() => node.animate({ position: pos }, { duration: 80 }), 80);
    }

    /* ═══════════════════════════════════════════════════════════════
       BIND TOOLBAR BUTTONS
    ═══════════════════════════════════════════════════════════════ */
    function bindButtons() {
        const on = (e, fn) => { if (e) e.addEventListener('click', fn); };

        on(el.fitBtn,         () => { cy?.fit(40); scheduleSave(); });
        on(el.expandAllBtn,   () => expandAll());
        on(el.collapseAllBtn, () => collapseAll());
        on(el.lockLayoutBtn,  () => { if (!window.IS_ADMIN || !cy) return; layoutLocked = !layoutLocked; applyLockState(); persistState(); });

        on(el.resetLayoutBtn, async () => {
            if (!window.IS_ADMIN) return;
            if (layoutLocked) { alert('Layout is locked. Unlock before Auto Adjust.'); return; }
            if (!cy) return;
            suppressSave = true;
            try {
                collapsedNodes.clear();
                cy.nodes().removeClass('collapsed hidden-child collapsed-child');
                cy.edges().removeClass('hidden-edge');
                cy.nodes().forEach(n => n.data('hiddenCount', 0));
                await runELK(true);
                persistState();
            } finally { suppressSave = false; }
        });

        on(el.pingBtn, async function () {
            const btn = el.pingBtn;
            btn.disabled = true;
            btn.innerHTML = cfg.mode === 'fullscreen'
                ? '<span class="spinner" style="width:12px;height:12px;border-width:2px;"></span> Pinging…'
                : '<span class="spinner-border spinner-border-sm me-1" style="width:12px;height:12px;"></span> Pinging…';
            try {
                await fetch('/api/ping/now');
                const poll = setInterval(async () => {
                    try {
                        const s = await fetch('/api/ping/status').then(r => r.json());
                        if (!s.running) {
                            clearInterval(poll);
                            const res = s.last_result || {};
                            showPingFlash(`<i class="fas fa-check-circle"></i> Ping done — Total:${res.total || 0} Up:${res.up || 0} Down:${res.down || 0} ${res.duration || 0}s`);
                            btn.innerHTML = '<i class="fas fa-check"></i> Done';
                            setTimeout(() => { btn.innerHTML = '<i class="fas fa-network-wired"></i> Ping All'; btn.disabled = false; }, 3000);
                            reloadTopology();
                        }
                    } catch {}
                }, 2000);
            } catch {
                btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
                btn.disabled  = false;
                setTimeout(() => { btn.innerHTML = '<i class="fas fa-network-wired"></i> Ping All'; }, 2200);
            }
        });

        on(el.refreshBtn, () => reloadTopology());

        /* fullscreen-only */
        on(el.exitBtn, () => { window.close(); if (window.opener) window.close(); else window.location.href = '/dashboard'; });

        /* category hide menu — dynamically populated */
        const catMenu = el.categoryMenu;
        if (catMenu) {
            const populateCategories = () => {
                if (catMenu.dataset.populated) return;
                const cats = new Map();
                cy.nodes().forEach(n => { const c = n.data('category'); if (c) cats.set(c, (cats.get(c) || 0) + 1); });
                if (!cats.size) return;
                const sorted = [...cats.entries()].sort((a, b) => a[0].localeCompare(b[0]));
                let html = sorted.map(([c, count]) =>
                    `<label class="dropdown-item d-flex align-items-center gap-2" style="font-size:12px;cursor:pointer;">
                        <input type="checkbox" class="cat-toggle me-1" value="${c}" checked> ${c}
                        <span class="badge bg-secondary ms-auto" style="font-size:10px;">${count}</span>
                    </label>`
                ).join('');
                html += `<div class="dropdown-divider my-1"></div>`;
                html += `<div class="d-flex gap-1 px-2">
                    <button type="button" class="btn btn-sm btn-outline-light flex-fill cat-select-all" style="font-size:11px;padding:2px 6px;">All</button>
                    <button type="button" class="btn btn-sm btn-outline-warning flex-fill cat-clear-all" style="font-size:11px;padding:2px 6px;">None</button>
                </div>`;
                catMenu.innerHTML = html;
                catMenu.querySelectorAll('.cat-toggle').forEach(cb => {
                    cb.addEventListener('change', function () {
                        if (this.checked) showCategory(this.value);
                        else hideCategory(this.value);
                    });
                });
                catMenu.querySelector('.cat-select-all')?.addEventListener('click', () => {
                    catMenu.querySelectorAll('.cat-toggle').forEach(cb => { cb.checked = true; });
                    showAllCategories();
                });
                catMenu.querySelector('.cat-clear-all')?.addEventListener('click', () => {
                    catMenu.querySelectorAll('.cat-toggle').forEach(cb => { cb.checked = false; });
                    const catsArr = [...cats.keys()];
                    catsArr.forEach(c => hideCategory(c));
                });
                catMenu.dataset.populated = '1';
            };
            catMenu.addEventListener('show.bs.dropdown', populateCategories);
        }

        /* search */
        const si = el.searchInput;
        if (si) si.addEventListener('keyup', e => {
            if (e.key !== 'Enter' || !cy) return;
            const term = e.target.value.toLowerCase().trim();
            if (!term) return;
            const found = cy.nodes().filter(n => {
                const d = n.data();
                return [d.label, d.id, d.device_name, d.hostname, d.location].some(v => v && String(v).toLowerCase().includes(term));
            });
            if (found.length) {
                if (found[0].hasClass('hidden-child')) {
                    let cur = found[0]; const toExp = [];
                    for (let i = 0; i < 25; i++) {
                        const pe = cy.edges(`[target="${cur.id()}"]`);
                        if (!pe.length) break;
                        const pid = pe[0].data('source');
                        if (collapsedNodes.has(pid)) toExp.push(pid);
                        cur = cy.nodes(`[id="${pid}"]`);
                    }
                    toExp.reverse().forEach(pid => expandNode(pid));
                }
                cy.animate({ center: { eles: found[0] }, zoom: 2.4 }, { duration: 500 });
                found[0].addClass('hovered');
                setTimeout(() => found[0].removeClass('hovered'), 2200);
            } else if (el.siteInfoPanel) {
                const sp = el.siteInfoPanel;
                if (sp) { sp.innerHTML = `<i class="fas fa-search-minus text-muted"></i> No match for "<em>${term}</em>"`; setTimeout(() => { sp.innerHTML = '<i class="fas fa-info-circle me-1"></i> Click any node to see details'; }, 2000); }
            }
        });

        /* legend toggle */
        const lt = el.legendToggle;
        if (lt) lt.addEventListener('click', () => {
            const lb = el.legendBox, li = el.legendIcon;
            if (!lb) return;
            lb.classList.toggle('collapsed');
            if (li) li.className = lb.classList.contains('collapsed') ? 'fas fa-chevron-right ms-auto' : 'fas fa-chevron-down ms-auto';
        });

        /* context menu items */
        const ctx = el.ctxMenu;
        if (ctx) {
            ctx.querySelector('#ctxOpenHTTP')?.addEventListener('click', () => {
                if (!ctxNode) return; closeCtxMenu();
                window.open('http://' + ctxNode.id(), '_blank', 'noopener,noreferrer');
            });
            ctx.querySelector('#ctxOpenHTTPS')?.addEventListener('click', () => {
                if (!ctxNode) return; closeCtxMenu();
                window.open('https://' + ctxNode.id(), '_blank', 'noopener,noreferrer');
            });
            ctx.querySelector('#ctxPing')?.addEventListener('click', () => {
                if (!ctxNode) return; const ip = ctxNode.id(); closeCtxMenu();
                fetch('/api/ping/' + ip).catch(() => {});
                showPingFlash(`<i class="fas fa-satellite-dish"></i> Pinging ${ip}…`);
            });
            ctx.querySelector('#ctxExpand')?.addEventListener('click', () => {
                if (!ctxNode) return; expandNode(ctxNode.id()); closeCtxMenu();
                cy.animate({ fit: { eles: cy.elements(':visible'), padding: 40 } }, { duration: 380 }); scheduleSave();
            });
            ctx.querySelector('#ctxCollapseNode')?.addEventListener('click', () => {
                if (!ctxNode) return; collapseNode(ctxNode.id()); closeCtxMenu();
                cy.animate({ fit: { eles: cy.elements(':visible'), padding: 40 } }, { duration: 380 }); scheduleSave();
            });
            ctx.querySelector('#ctxDetails')?.addEventListener('click', () => {
                if (!ctxNode) return; closeCtxMenu();
                const d = ctxNode.data(), t = el.modalTitle, b = el.modalBody;
                if (!t || !b) return;
                const isDark = cfg.mode === 'fullscreen';
                const fields = [
                    ['Hostname', d.hostname || d.device_name],
                    ['IP', d.id || d.ip],
                    ['Status', d.status],
                    ['Category', d.category],
                    ['Location', d.location],
                    ['Children', d.hasChildren ? (d.childCount || '?') + ' total' : '—'],
                    ['Up', d.upChildren ? d.upChildren + '' : '—'],
                    ['Down', d.downChildren ? d.downChildren + '' : '—'],
                ];
                t.innerHTML = `<i class="fas fa-server me-2" style="color:#3b82f6;"></i>${d.hostname || d.device_name || d.id}`;
                b.innerHTML = `<table style="width:100%;font-size:13px;border-collapse:collapse;">` +
                    fields.filter(([, v]) => v && v !== '—')
                    .map(([k, v]) => `<tr><th style="width:35%;color:${isDark ? '#94a3b8' : '#64748b'};font-weight:600;text-align:left;padding:4px 0;">${k}</th><td style="color:${isDark ? '#e2e8f0' : 'inherit'};">${v}</td></tr>`).join('') +
                    `</table>`;
                showModal();
            });
        }

        /* modal close */
        on(el.modalClose, hideModal);
        const mo = el.modalOverlay;
        if (mo) mo.addEventListener('click', e => { if (e.target === mo) hideModal(); });

        /* close ctx on outside click */
        document.addEventListener('click',       () => closeCtxMenu());
        document.addEventListener('contextmenu', e => { if (!e.target.closest(cfg.cyContainer)) closeCtxMenu(); });

        /* alert ticker pause on hover */
        const al = el.alertList;
        if (al) { al.addEventListener('mouseenter', () => { alertPaused = true; }); al.addEventListener('mouseleave', () => { alertPaused = false; }); }
    }

    /* ═══════════════════════════════════════════════════════════════
       RELOAD
    ═══════════════════════════════════════════════════════════════ */
    function reloadTopology() {
        if (cy) { cy.destroy(); cy = null; }
        const cyEl   = el.cy;
        const loadEl = el.loading;
        if (cyEl)   cyEl.style.display   = 'none';
        if (loadEl) loadEl.style.display = cfg.mode === 'fullscreen' ? 'flex' : 'flex';
        loadGraph(); loadAlerts(); loadDevices();
    }

    /* ═══════════════════════════════════════════════════════════════
       SOCKET.IO
    ═══════════════════════════════════════════════════════════════ */
    function initSocket() {
        try {
            const socket = io();
            socket.on('monitor_heartbeat', () => { lastHeartbeat = Date.now(); });
            socket.on('device_status_update', data => {
                if (!cy) return;
                (data.changes || []).forEach(ch => {
                    const node = cy.nodes(`[id="${ch.id}"]`);
                    if (node.length) {
                        const oldStatus = node.data('status');
                        const newStatus = ch.status ? 'GREEN' : 'RED';
                        if (oldStatus !== newStatus) {
                            node.data('status', newStatus);
                            updateParentStatus(ch.id);
                            if (oldStatus === 'RED'   && newStatus === 'GREEN') animateRecovery(node);
                            if (oldStatus === 'GREEN' && newStatus === 'RED')   animateFailure(node);
                        }
                    }
                });
                loadDevices();
                updateLastPoll();
            });
            socket.on('dashboard_updated', state => {
                if (!cy) return;
                suppressSave = true;
                const positions = state.node_positions || {};
                if (Object.keys(positions).length) cy.nodes().forEach(n => { if (positions[n.id()]) n.position(positions[n.id()]); });
                collapsedNodes.clear();
                (state.collapsed || []).forEach(id => collapsedNodes.add(id));
                cy.nodes().forEach(n => n.removeClass('collapsed hidden-child collapsed-child'));
                cy.edges().forEach(e => e.removeClass('hidden-edge'));
                tagParentNodes(); buildHierarchyMaps(); computeAggregationStatus(); computeDepthMap(); detectSharedNodes();
                collapsedNodes.forEach(nid => { const node = cy.nodes(`[id="${nid}"]`); if (node.length) { node.addClass('collapsed'); hideDescendants(nid); } });

                /* Restore hidden categories */
                /* Restore hidden categories */
                hiddenCategories.clear();
                (state.hidden_categories || []).forEach(cat => hiddenCategories.add(cat));
                cy.nodes().forEach(node => {
                    const cat = node.data('category');
                    if (cat && hiddenCategories.has(cat) && !node.data('hasChildren')) {
                        node.addClass('hidden-child');
                        node.connectedEdges().forEach(e => e.addClass('hidden-edge'));
                    }
                });
                /* sync viewport only if not drifted */
                if (cfg.mode === 'dashboard') {
                    const cp = cy.pan(), cz = cy.zoom();
                    const moved = Math.abs(cp.x - (state.pan_x || 0)) > 2 || Math.abs(cp.y - (state.pan_y || 0)) > 2 || Math.abs(cz - (state.zoom || 1)) > 0.06;
                    if (!moved) { cy.zoom(state.zoom || 1); cy.pan({ x: state.pan_x || 0, y: state.pan_y || 0 }); }
                }
                layoutLocked = !!state.layout_locked;
                applyLockState();
                suppressSave = false;
            });
        } catch {}
    }

    /* ═══════════════════════════════════════════════════════════════
       PUBLIC INIT
    ═══════════════════════════════════════════════════════════════ */
    window.initTopology = function (config) {
        cfg = config;

        /* Resolve all element references once — no repeated querySelector calls */
        const map = {
            cy:           cfg.cyContainer,
            loading:      cfg.loadingEl,
            pingFlash:    cfg.pingFlashEl,
            syncBadge:    cfg.syncBadgeEl,
            fitBtn:       cfg.fitBtn,
            expandAllBtn: cfg.expandAllBtn,
            collapseAllBtn: cfg.collapseAllBtn,
            resetLayoutBtn: cfg.resetLayoutBtn,
            lockLayoutBtn: cfg.lockLayoutBtn,
            pingBtn:      cfg.pingBtn,
            refreshBtn:   cfg.refreshBtn,
            searchInput:  cfg.searchInput,
            legendBox:    cfg.legendBox,
            legendToggle: cfg.legendToggle,
            legendIcon:   cfg.legendIcon,
            nodeTooltip:  cfg.nodeTooltip,
            ctxMenu:      cfg.ctxMenu,
            modalOverlay: cfg.modalOverlay,
            modalTitle:   cfg.modalTitle,
            modalBody:    cfg.modalBody,
            modalClose:   cfg.modalClose,
            minimap:      cfg.minimapEl,
            kpiTotal:     cfg.kpiTotal,
            kpiUp:        cfg.kpiUp,
            kpiDown:      cfg.kpiDown,
            kpiAlerts:    cfg.kpiAlerts,
            downDevices:  cfg.downDevices,
            activeAlerts: cfg.activeAlerts,
            lastPoll:     cfg.lastPoll,
            alertList:    cfg.alertList,
            alertCount:   cfg.alertCount,
            categoryContainer: cfg.categoryContainer,
            categoryCount: cfg.categoryCount,
            siteInfoPanel: cfg.siteInfoPanel,
            alertPanel:   cfg.alertPanel,
            exitBtn:      cfg.exitBtn,
            categoryMenu:    cfg.categoryMenu,
            sharedLegend:    cfg.sharedLegend,
        };
        for (const [key, sel] of Object.entries(map)) {
            el[key] = $el(sel);
        }

        /* RBAC: hide admin-only buttons for viewers */
        if (!window.IS_ADMIN) {
            [el.lockLayoutBtn, el.resetLayoutBtn].forEach(e => { if (e) e.style.display = 'none'; });
        }

        bindButtons();
        initSocket();

        window.addEventListener('load', () => {
            updateLastPoll();
            loadAlerts();
            loadDevices();
            loadGraph();
            setInterval(() => { loadAlerts(); loadDevices(); updateLastPoll(); }, 28000);
        });
    };

})();
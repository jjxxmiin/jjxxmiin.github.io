(function () {
  'use strict';

  var reader = document.querySelector('[data-book-reader]');
  if (!reader) return;
  if (document.documentElement.classList.contains('book-js-failed')) return;

  var pages = Array.prototype.slice.call(reader.querySelectorAll('[data-book-page]'));
  var pageContainer = reader.querySelector('[data-book-pages]');
  var stage = reader.querySelector('[data-book-stage]');
  var previousButton = reader.querySelector('[data-book-prev]');
  var nextButton = reader.querySelector('[data-book-next]');
  var startButton = reader.querySelector('[data-book-start]');
  var startLabel = reader.querySelector('[data-book-start-label]');
  var restartButton = reader.querySelector('[data-book-restart]');
  var shareButton = reader.querySelector('[data-book-share]');
  var afterwordButton = reader.querySelector('[data-book-afterword]');
  var afterwordPanel = document.getElementById('book-afterword');
  var scrollAdTemplate = reader.querySelector('[data-book-scroll-ad-template]');
  var siteTail = document.getElementById('tail-wrapper');
  var viewButton = reader.querySelector('[data-book-view-toggle]');
  var themeButton = reader.querySelector('[data-book-theme]');
  var tocDialog = reader.querySelector('[data-book-toc]');
  var tocList = reader.querySelector('[data-book-toc-list]');
  var tocOpen = reader.querySelector('[data-book-toc-open]');
  var tocClose = reader.querySelector('[data-book-toc-close]');
  var currentNode = reader.querySelector('[data-book-current]');
  var totalNode = reader.querySelector('[data-book-total]');
  var currentLabel = reader.querySelector('[data-book-current-label]');
  var progressBar = reader.querySelector('[data-book-progress]');
  var announcer = reader.querySelector('[data-book-announcer]');
  var storageKey = 'opsoai:visual-book:' + (reader.getAttribute('data-book-path') || window.location.pathname);
  var currentIndex = 0;
  var scrollView = false;
  var viewedPages = {};
  var pointerStart = null;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var spreadMedia = window.matchMedia && window.matchMedia('(min-width: 1024px)');
  var initialPaginationKey = paginationKey();
  var viewportResizeTimer = null;
  var mermaidSources = [];
  var mermaidRenderSequence = 0;
  var mermaidConfigured = false;
  var scrollAd = null;

  function clearFallbackTimer() {
    if (!window.__opsoaiBookFallback) return;
    window.clearTimeout(window.__opsoaiBookFallback);
    window.__opsoaiBookFallback = null;
  }

  function failOpen() {
    clearFallbackTimer();
    document.documentElement.classList.remove('book-js');
    document.documentElement.classList.add('book-js-failed');
  }

  /*
   * Chirpy normally renders every Mermaid block on DOMContentLoaded. Book pages
   * that are not open are 0x0 at that point, which produces a broken 16px SVG.
   * Preserve the source now and opt these blocks out of that eager pass. They
   * are rendered below only after their physical page becomes visible.
   */
  reader.querySelectorAll('pre code.language-mermaid, code.language-mermaid').forEach(function (code) {
    var sourceIndex = mermaidSources.length;
    var sourceHost = code.closest('pre') || code;
    var generatedHost = sourceHost.nextElementSibling;
    mermaidSources.push(code.textContent || '');
    if (generatedHost && generatedHost.classList.contains('mermaid')) {
      generatedHost.classList.remove('mermaid');
      generatedHost.classList.add('book-mermaid-pending');
      generatedHost.setAttribute('data-book-mermaid-index', String(sourceIndex));
      sourceHost.remove();
    } else {
      code.classList.remove('language-mermaid');
      code.classList.add('language-book-mermaid');
      sourceHost.setAttribute('data-book-mermaid-index', String(sourceIndex));
    }
  });

  function pad(value) {
    return String(value).padStart(2, '0');
  }

  function cleanHeading(heading) {
    if (!heading) return '';
    var clone = heading.cloneNode(true);
    Array.prototype.slice.call(clone.querySelectorAll('.anchor')).forEach(function (anchor) {
      anchor.remove();
    });
    return (clone.textContent || '').replace(/·/g, ', ').replace(/\s+/g, ' ').trim();
  }

  function splitLongLists(content) {
    var chunkSize = window.innerHeight <= 650 ? 2 : 3;
    Array.prototype.slice.call(content.children).forEach(function (list) {
      if (!/^(UL|OL)$/.test(list.tagName)) return;
      var items = Array.prototype.slice.call(list.children).filter(function (item) {
        return item.tagName === 'LI';
      });
      if (items.length <= chunkSize) return;

      var fragment = document.createDocumentFragment();
      var orderedStart = parseInt(list.getAttribute('start'), 10) || 1;
      for (var offset = 0; offset < items.length; offset += chunkSize) {
        var nextList = list.cloneNode(false);
        if (list.tagName === 'OL') nextList.setAttribute('start', String(orderedStart + offset));
        items.slice(offset, offset + chunkSize).forEach(function (item) {
          nextList.appendChild(item);
        });
        fragment.appendChild(nextList);
      }
      list.replaceWith(fragment);
    });
  }

  function splitLongCallouts(content) {
    var chunkSize = window.innerHeight <= 650 ? 1 : 2;
    Array.prototype.slice.call(content.children).forEach(function (callout) {
      if (!callout.matches('blockquote, .prompt-info, .prompt-tip, .prompt-warning, .prompt-danger')) return;
      var list = callout.querySelector(':scope > ul, :scope > ol');
      if (!list) return;
      var items = Array.prototype.slice.call(list.children).filter(function (item) {
        return item.tagName === 'LI';
      });
      if (items.length <= chunkSize) return;

      var children = Array.prototype.slice.call(callout.children);
      var listIndex = children.indexOf(list);
      var before = children.slice(0, listIndex);
      var after = children.slice(listIndex + 1);
      var orderedStart = parseInt(list.getAttribute('start'), 10) || 1;
      var fragment = document.createDocumentFragment();

      for (var offset = 0; offset < items.length; offset += chunkSize) {
        var nextCallout = callout.cloneNode(false);
        var nextList = list.cloneNode(false);
        if (offset === 0) before.forEach(function (node) { nextCallout.appendChild(node); });
        if (list.tagName === 'OL') nextList.setAttribute('start', String(orderedStart + offset));
        items.slice(offset, offset + chunkSize).forEach(function (item) {
          nextList.appendChild(item);
        });
        nextCallout.appendChild(nextList);
        if (offset + chunkSize >= items.length) {
          after.forEach(function (node) { nextCallout.appendChild(node); });
        }
        fragment.appendChild(nextCallout);
      }

      callout.replaceWith(fragment);
    });
  }

  function splitLongTables(content) {
    var chunkSize = window.innerHeight <= 650 ? 1 : 3;
    Array.prototype.slice.call(content.children).forEach(function (block) {
      var table = block.matches('table') ? block : block.querySelector(':scope > table');
      if (!table || !table.tBodies.length) return;

      var headers = Array.prototype.slice.call(table.querySelectorAll('thead th')).map(function (cell) {
        return (cell.textContent || '').replace(/\s+/g, ' ').trim();
      });
      var body = table.tBodies[0];
      var rows = Array.prototype.slice.call(body.rows);

      rows.forEach(function (row) {
        Array.prototype.slice.call(row.cells).forEach(function (cell, index) {
          cell.setAttribute('data-book-cell-label', headers[index] || '항목');
          if (!cell.querySelector(':scope > .book-cell-value')) {
            var value = document.createElement('span');
            value.className = 'book-cell-value';
            while (cell.firstChild) value.appendChild(cell.firstChild);
            cell.appendChild(value);
          }
        });
      });

      if (rows.length <= chunkSize) return;

      var fragment = document.createDocumentFragment();
      for (var offset = 0; offset < rows.length; offset += chunkSize) {
        var nextTable = table.cloneNode(false);
        Array.prototype.slice.call(table.children).forEach(function (child) {
          if (/^(CAPTION|COLGROUP|THEAD)$/.test(child.tagName)) {
            nextTable.appendChild(child.cloneNode(true));
          }
        });

        var nextBody = body.cloneNode(false);
        rows.slice(offset, offset + chunkSize).forEach(function (row) {
          nextBody.appendChild(row);
        });
        nextTable.appendChild(nextBody);

        if (offset + chunkSize >= rows.length && table.tFoot) {
          nextTable.appendChild(table.tFoot.cloneNode(true));
        }

        if (block === table) fragment.appendChild(nextTable);
        else {
          var nextBlock = block.cloneNode(false);
          nextBlock.appendChild(nextTable);
          fragment.appendChild(nextBlock);
        }
      }
      block.replaceWith(fragment);
    });
  }

  function blockKind(block) {
    if (!block || block.nodeType !== Node.ELEMENT_NODE) return 'text';
    if (block.matches('.proj')) return 'project';
    if (block.matches('.chartjs-wrap') || block.querySelector('.language-chartjs')) return 'chart';
    if (
      block.matches('.mermaid, [data-book-mermaid-index]') ||
      block.querySelector('.language-book-mermaid, .language-mermaid')
    ) return 'flow';
    if (block.matches('.table-wrapper') || block.querySelector('table')) return 'table';
    if (block.matches('figure, .book-prologue-art') || block.querySelector('img, picture, video, iframe')) return 'visual';
    if (block.matches('pre, .highlight') || block.querySelector('pre')) return 'code';
    if (block.matches('ul, ol')) return 'list';
    return 'text';
  }

  function blockCost(block) {
    var textLength = (block.textContent || '').replace(/\s+/g, ' ').trim().length;
    var listItems = block.querySelectorAll ? block.querySelectorAll('li').length : 0;
    return textLength + listItems * 24;
  }

  function packPageBlocks(blocks) {
    var groups = [];
    var current = null;
    var shortViewport = window.innerHeight <= 650;

    function flush() {
      if (current && current.nodes.length) groups.push(current);
      current = null;
    }

    blocks.forEach(function (block) {
      var kind = blockKind(block);
      var cost = blockCost(block);
      var headingLike = /^(H3|H4|H5|H6)$/.test(block.tagName);

      if (kind !== 'text') {
        flush();
        current = { nodes: [block], kind: kind, cost: 320, substantive: 1 };
        return;
      }

      if (current && current.kind !== 'text') {
        var canCaptionVisual = false;
        if (canCaptionVisual) {
          current.nodes.push(block);
          current.cost += cost;
          flush();
          return;
        }
        flush();
      }

      if (!current) current = { nodes: [], kind: 'text', cost: 0, substantive: 0 };

      if (headingLike && current.nodes.length) {
        flush();
        current = { nodes: [], kind: 'text', cost: 0, substantive: 0 };
      }

      var isSubstantive = !headingLike;
      var wouldOverflow =
        current.nodes.length &&
        isSubstantive &&
        current.substantive > 0 &&
        (current.cost + cost > (shortViewport ? 240 : 370) || current.substantive >= (shortViewport ? 1 : 2));

      if (wouldOverflow) {
        flush();
        current = { nodes: [], kind: 'text', cost: 0, substantive: 0 };
      }

      current.nodes.push(block);
      current.cost += cost;
      if (isSubstantive) current.substantive += 1;
    });

    flush();
    return groups.length ? groups : [{ nodes: [], kind: 'text', cost: 0, substantive: 0 }];
  }

  function chunkLabel(kind) {
    if (kind === 'project') return '프로젝트';
    if (kind === 'chart') return '그래프';
    if (kind === 'flow') return '흐름도';
    if (kind === 'table') return '비교표';
    if (kind === 'visual') return '한 장면';
    if (kind === 'code') return '코드';
    if (kind === 'list') return '목록';
    return '이어읽기';
  }

  function paginateContent() {
    var semanticPages = pages.slice();

    semanticPages.forEach(function (template) {
      if (!template.classList.contains('book-content-page')) return;
      var content = template.querySelector('.book-page-content');
      if (!content) return;

      /* The project facts card used to sit outside the measured content and
       * was cloned onto every continuation page. Move it into the page packer
       * and give it a dedicated leaf so its real height is always respected. */
      var projectCard = template.querySelector('.book-page-scroll > .proj');
      if (projectCard) content.insertBefore(projectCard, content.firstChild);

      splitLongCallouts(content);
      splitLongLists(content);
      splitLongTables(content);
      var heading = content.querySelector(':scope > h2');
      var baseLabel = template.getAttribute('data-book-label') || cleanHeading(heading) || '들어가며';
      var blocks = Array.prototype.slice.call(content.children).filter(function (child) {
        return child !== heading;
      });
      var groups = packPageBlocks(blocks);
      if (groups.length === 1) return;

      var cleanShell = template.cloneNode(true);
      var cleanContent = cleanShell.querySelector('.book-page-content');
      cleanContent.textContent = '';
      var insertAfter = template;

      groups.forEach(function (group, groupIndex) {
        var page = groupIndex === 0 ? template : cleanShell.cloneNode(true);
        var pageContent = page.querySelector('.book-page-content');
        var continuation = groupIndex > 0;
        pageContent.textContent = '';

        if (heading && groupIndex === 0) pageContent.appendChild(heading);

        group.nodes.forEach(function (node) { pageContent.appendChild(node); });
        page.setAttribute('data-book-part', String(groupIndex + 1));
        page.setAttribute('data-book-parts', String(groups.length));
        page.setAttribute('data-book-chunk-kind', group.kind);
        if (continuation) {
          page.setAttribute('data-book-continuation', 'true');
          page.setAttribute('data-book-label', baseLabel + ' / ' + chunkLabel(group.kind));
        } else {
          page.removeAttribute('data-book-continuation');
          page.setAttribute('data-book-label', baseLabel);
        }

        var chapterMark = page.querySelector('.book-page-folio > span:first-child');
        if (chapterMark && groups.length > 1) {
          chapterMark.textContent = chapterMark.textContent.replace(/\s+\/\s+\d+\/\d+$/, '') +
            ' / ' + (groupIndex + 1) + '/' + groups.length;
        }

        if (continuation) {
          insertAfter.insertAdjacentElement('afterend', page);
          insertAfter = page;
        }
      });
    });

    pages = Array.prototype.slice.call(reader.querySelectorAll('[data-book-page]'));
  }

  function labelPages() {
    pages.forEach(function (page, index) {
      var kind = page.getAttribute('data-book-kind');
      var heading = page.querySelector('.book-page-content > h2');
      var label = page.getAttribute('data-book-label') || cleanHeading(heading);

      if (!label) label = kind === 'finish' ? '완독' : '들어가며';
      page.setAttribute('data-book-label', label);
      page.setAttribute('aria-label', pad(index + 1) + '쪽, ' + label);

      if (heading) {
        var chapter = parseInt(page.getAttribute('data-book-chapter'), 10);
        heading.setAttribute('data-book-number', 'CHAPTER ' + pad(isNaN(chapter) ? index : chapter));
        if (!heading.id) heading.id = 'chapter-' + pad(isNaN(chapter) ? index : chapter);
        page.setAttribute('aria-labelledby', heading.id);
      }

      var folio = page.querySelector('[data-book-folio]');
      if (folio) folio.textContent = pad(index + 1);

      page.addEventListener('beforematch', function () {
        if (!scrollView) showPage(index, { updateHash: false, focus: false });
      });
    });
  }

  function topicIcon(page) {
    var subject = [
      page.getAttribute('data-book-label') || '',
      reader.getAttribute('data-book-title') || '',
      reader.getAttribute('data-book-category') || ''
    ].join(' ').toLowerCase();
    var profiles = [
      { pattern: /보안|위협|공격|취약|딥페이크|프라이버시|security|cyber|threat|attack|privacy/, icon: 'fa-solid fa-shield-halved' },
      { pattern: /가격|요금|비용|플랜|비교|선택|pricing|price|comparison|\bcosts?\b|\bplans?\b/, icon: 'fa-solid fa-scale-balanced' },
      { pattern: /일자리|직업|취업|커리어|업무|생산성|\bjobs?\b|\bcareer\b|\bwork\b|productiv/, icon: 'fa-solid fa-briefcase' },
      { pattern: /수학|방정식|확률|통계|계산|math|formula|equation|probability|statistic/, icon: 'fa-solid fa-square-root-variable' },
      { pattern: /설치|사용법|방법|가이드|튜토리얼|시작|guide|tutorial|how to|setup|install/, icon: 'fa-solid fa-compass' },
      { pattern: /디자인|시각|사용자 경험|\bui\b|\bux\b|design|visual/, icon: 'fa-solid fa-palette' },
      { pattern: /금융|투자|주식|시장|finance|invest|stock|market/, icon: 'fa-solid fa-chart-line' },
      { pattern: /의료|건강|임상|health|medical|clinical/, icon: 'fa-solid fa-heart-pulse' },
      { pattern: /코드|코딩|개발|프로그래밍|\bapi\b|developer|coding|programming/, icon: 'fa-solid fa-code' },
      { pattern: /인공지능|에이전트|모델|\bai\b|agent|model|llm/, icon: 'fa-solid fa-microchip' }
    ];

    for (var index = 0; index < profiles.length; index += 1) {
      if (profiles[index].pattern.test(subject)) return profiles[index].icon;
    }
    return 'fa-solid fa-book-open';
  }

  function decoratePages() {
    pages.forEach(function (page) {
      var content = page.querySelector('.book-page-content');
      var folio = page.querySelector('.book-page-folio');
      var heading = content && content.querySelector(':scope > h2');
      if (!content || !folio) return;

      var visual = { icon: topicIcon(page), label: 'READ' };
      if (content.querySelector('.chartjs-wrap, .language-chartjs')) {
        visual = { icon: 'fa-solid fa-chart-column', label: 'DATA' };
      } else if (content.querySelector('.proj')) {
        visual = {
          icon: content.querySelector('.proj.is-github') ? 'fa-brands fa-github' : 'fa-solid fa-cube',
          label: 'PROJECT'
        };
      } else if (content.querySelector('.mermaid, .language-mermaid, .language-book-mermaid, [data-book-mermaid-index]')) {
        visual = { icon: 'fa-solid fa-diagram-project', label: 'FLOW' };
      } else if (content.querySelector('figure, img, .book-prologue-art')) {
        visual = { icon: 'fa-regular fa-image', label: 'VISUAL' };
      } else if (content.querySelector('table')) {
        visual = { icon: 'fa-solid fa-table-cells-large', label: 'COMPARE' };
      } else if (content.querySelector('pre, .highlight')) {
        visual = { icon: 'fa-solid fa-code', label: 'CODE' };
      }

      page.setAttribute('data-book-visual', visual.label.toLowerCase());

      if (heading) {
        var badge = document.createElement('span');
        var badgeIcon = document.createElement('i');
        badge.className = 'book-chapter-icon';
        badge.setAttribute('aria-hidden', 'true');
        badgeIcon.className = visual.icon;
        badge.appendChild(badgeIcon);
        heading.insertBefore(badge, heading.firstChild);
      }

      if (visual.label === 'READ') {
        var emblem = document.createElement('span');
        var emblemIcon = document.createElement('i');
        emblem.className = 'book-page-emblem';
        emblem.setAttribute('aria-hidden', 'true');
        emblemIcon.className = visual.icon;
        emblem.appendChild(emblemIcon);
        page.appendChild(emblem);
      }

      var marker = document.createElement('span');
      var markerIconWrap = document.createElement('b');
      var markerIcon = document.createElement('i');
      var markerLabel = document.createElement('span');
      marker.className = 'book-page-kind';
      marker.setAttribute('aria-hidden', 'true');
      markerIcon.className = visual.icon;
      markerLabel.textContent = visual.label;
      markerIconWrap.appendChild(markerIcon);
      marker.appendChild(markerIconWrap);
      marker.appendChild(markerLabel);
      folio.insertBefore(marker, folio.lastElementChild);
    });
  }

  function linkBrand(href) {
    var hostname = '';
    try {
      hostname = new URL(href, window.location.href).hostname.toLowerCase().replace(/^www\./, '');
    } catch (_) {
      return { icon: 'fa-solid fa-arrow-up-right-from-square', name: '', host: '' };
    }

    var brands = [
      { domains: ['github.com'], icon: 'fa-brands fa-github', name: 'GitHub' },
      { domains: ['apple.com'], icon: 'fa-brands fa-apple', name: 'Apple' },
      { domains: ['microsoft.com'], icon: 'fa-brands fa-microsoft', name: 'Microsoft' },
      { domains: ['google.com', 'google.dev'], icon: 'fa-brands fa-google', name: 'Google' },
      { domains: ['youtube.com', 'youtu.be'], icon: 'fa-brands fa-youtube', name: 'YouTube' },
      { domains: ['x.com', 'twitter.com'], icon: 'fa-brands fa-x-twitter', name: 'X' },
      { domains: ['linkedin.com'], icon: 'fa-brands fa-linkedin', name: 'LinkedIn' },
      { domains: ['medium.com'], icon: 'fa-brands fa-medium', name: 'Medium' },
      { domains: ['npmjs.com'], icon: 'fa-brands fa-npm', name: 'npm' },
      { domains: ['python.org', 'pypi.org'], icon: 'fa-brands fa-python', name: 'Python' },
      { domains: ['discord.com', 'discord.gg'], icon: 'fa-brands fa-discord', name: 'Discord' },
      { domains: ['reddit.com'], icon: 'fa-brands fa-reddit', name: 'Reddit' },
      { domains: ['stackoverflow.com'], icon: 'fa-brands fa-stack-overflow', name: 'Stack Overflow' }
    ];

    for (var brandIndex = 0; brandIndex < brands.length; brandIndex += 1) {
      var brand = brands[brandIndex];
      var matches = brand.domains.some(function (domain) {
        return hostname === domain || hostname.endsWith('.' + domain);
      });
      if (matches) return { icon: brand.icon, name: brand.name, host: hostname };
    }

    return {
      icon: hostname ? 'fa-solid fa-globe' : 'fa-solid fa-arrow-up-right-from-square',
      name: '',
      host: hostname
    };
  }

  function buildSourceButtons() {
    function makeBox(links) {
      var box = document.createElement('div');
      box.className = 'post-links';

      links.forEach(function (link) {
        var href = link.getAttribute('href') || '';
        var brand = linkBrand(href);
        var newLink = document.createElement('a');
        var iconNode = document.createElement('i');
        var textNode = document.createElement('span');

        newLink.href = href;
        newLink.className = 'post-link';
        if (brand.host) newLink.setAttribute('data-book-host', brand.host);
        if (brand.name) newLink.setAttribute('data-book-brand', brand.name.toLowerCase().replace(/\s+/g, '-'));
        if (/^https?:/.test(href)) {
          newLink.target = '_blank';
          newLink.rel = 'noopener noreferrer';
        }
        iconNode.className = brand.icon;
        iconNode.setAttribute('aria-hidden', 'true');
        textNode.textContent = link.textContent;
        newLink.appendChild(iconNode);
        newLink.appendChild(textNode);
        if (/^https?:/.test(href)) {
          var newWindowLabel = document.createElement('span');
          newWindowLabel.className = 'visually-hidden';
          newWindowLabel.textContent = ', 새 창';
          newLink.appendChild(newWindowLabel);
        }
        box.appendChild(newLink);
      });

      return box;
    }

    reader.querySelectorAll('.book-page-content').forEach(function (content) {
      Array.prototype.slice.call(content.children).forEach(function (paragraph) {
        if (paragraph.tagName !== 'P') return;
        var links = Array.prototype.slice.call(paragraph.querySelectorAll(':scope > a'));
        if (links.length < 2) return;

        var onlyLinksAndPipes = Array.prototype.slice.call(paragraph.childNodes).every(function (node) {
          if (node.nodeType === Node.ELEMENT_NODE) return node.tagName === 'A';
          return node.nodeType !== Node.TEXT_NODE || !/[^\s|]/.test(node.textContent || '');
        });

        if (onlyLinksAndPipes) paragraph.replaceWith(makeBox(links));
      });

      Array.prototype.slice.call(content.querySelectorAll('.table-wrapper')).forEach(function (wrapper) {
        var table = wrapper.querySelector('table');
        if (!table || table.querySelectorAll('tr').length !== 1) return;
        var cells = Array.prototype.slice.call(table.querySelectorAll('td, th'));
        if (cells.length < 2) return;
        var links = [];
        var isLinkRow = cells.every(function (cell) {
          var anchors = cell.querySelectorAll('a');
          if (anchors.length !== 1 || cell.textContent.trim() !== anchors[0].textContent.trim()) return false;
          links.push(anchors[0]);
          return true;
        });
        if (isLinkRow) wrapper.replaceWith(makeBox(links));
      });
    });
  }

  function buildToc() {
    if (!tocList) return;
    tocList.textContent = '';

    pages.forEach(function (page, index) {
      if (
        page.getAttribute('data-book-kind') === 'cover' ||
        page.getAttribute('data-book-continuation') === 'true'
      ) return;
      var label = page.getAttribute('data-book-label');
      var item = document.createElement('li');
      var button = document.createElement('button');
      var number = document.createElement('span');
      var title = document.createElement('span');
      var pageNumber = document.createElement('span');

      button.type = 'button';
      button.setAttribute('data-book-goto', String(index));
      button.setAttribute('aria-label', pad(index + 1) + '쪽 ' + label + '로 이동');
      number.className = 'book-toc-number';
      number.textContent = page.getAttribute('data-book-kind') === 'finish' ? 'END' : pad(index);
      title.className = 'book-toc-title';
      title.textContent = label;
      pageNumber.className = 'book-toc-page';
      pageNumber.textContent = pad(index + 1);

      button.appendChild(number);
      button.appendChild(title);
      button.appendChild(pageNumber);
      item.appendChild(button);
      tocList.appendChild(item);
    });
  }

  function safeStorageGet() {
    try {
      return window.localStorage.getItem(storageKey);
    } catch (_) {
      return null;
    }
  }

  function safeStorageSet(value) {
    try {
      window.localStorage.setItem(storageKey, String(value));
    } catch (_) {
      // Reading must keep working when storage is unavailable.
    }
  }

  function track(eventName, parameters) {
    if (typeof window.gtag !== 'function') return;
    var data = Object.assign(
      {
        book_path: reader.getAttribute('data-book-path') || window.location.pathname,
        book_title: reader.getAttribute('data-book-title') || document.title
      },
      parameters || {}
    );
    window.gtag('event', eventName, data);
  }

  function initializeBookAds(scope) {
    if (!scope || !document.querySelector('script[src*="adsbygoogle"]')) return;

    scope.querySelectorAll('[data-book-ad]').forEach(function (container) {
      var slot = container.querySelector('.adsbygoogle');
      if (
        !slot ||
        slot.getAttribute('data-book-ad-requested') === 'true' ||
        slot.hasAttribute('data-adsbygoogle-status')
      ) return;

      slot.setAttribute('data-book-ad-requested', 'true');
      try {
        (window.adsbygoogle = window.adsbygoogle || []).push({});
        track('book_ad_request', {
          ad_placement: container.getAttribute('data-book-ad-placement') || 'book'
        });
      } catch (_) {
        slot.removeAttribute('data-book-ad-requested');
      }
    });
  }

  function ensureScrollAd() {
    if (scrollAd || !scrollAdTemplate || !pageContainer) return scrollAd;
    var contentPages = pages.filter(function (page) {
      return page.classList.contains('book-content-page');
    });
    if (!contentPages.length) return null;

    var anchorIndex = Math.min(
      contentPages.length - 1,
      Math.max(0, Math.floor(contentPages.length * 0.45))
    );
    var fragment = scrollAdTemplate.content.cloneNode(true);
    scrollAd = fragment.firstElementChild;
    contentPages[anchorIndex].insertAdjacentElement('afterend', scrollAd);
    window.requestAnimationFrame(function () { initializeBookAds(scrollAd); });
    return scrollAd;
  }

  function syncAfterword(available) {
    if (!afterwordPanel) return;

    if (!available) {
      document.body.classList.remove('book-afterword-ready', 'book-afterword-open');
      if (afterwordButton) afterwordButton.setAttribute('aria-expanded', 'false');
      afterwordPanel.hidden = true;
      if (siteTail) siteTail.hidden = true;
      return;
    }

    document.body.classList.add('book-afterword-ready');
    afterwordPanel.hidden = false;
    if (siteTail) siteTail.hidden = false;
    window.requestAnimationFrame(function () { initializeBookAds(afterwordPanel); });
  }

  function openAfterword() {
    syncAfterword(true);
    document.body.classList.add('book-afterword-open');
    if (afterwordButton) afterwordButton.setAttribute('aria-expanded', 'true');
    window.requestAnimationFrame(function () {
      afterwordPanel.focus({ preventScroll: true });
      (afterwordPanel || siteTail).scrollIntoView({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: 'start'
      });
    });
  }

  function resizeVisuals(pageList) {
    if (!pageList) return;
    if (!Array.isArray(pageList)) pageList = [pageList];
    renderMermaids(pageList);
    window.requestAnimationFrame(function () {
      pageList.forEach(function (page) {
        page.querySelectorAll('canvas').forEach(function (canvas) {
          if (window.Chart && typeof window.Chart.getChart === 'function') {
            var chart = window.Chart.getChart(canvas);
            if (chart) {
              chart.resize();
              if (!reduceMotion && !canvas.getAttribute('data-book-animated')) {
                if (typeof chart.reset === 'function') chart.reset();
                if (typeof chart.update === 'function') chart.update();
                canvas.setAttribute('data-book-animated', 'true');
              }
            }
          }
        });
        fitPageToViewport(page);
      });
    });
  }

  function fitPageToViewport(page) {
    if (!page || scrollView) return;
    var scroller = page.querySelector('.book-page-scroll');
    if (!scroller) return;

    page.classList.remove('book-density-compact', 'book-density-tight', 'is-book-overflowing');
    if (scroller.scrollHeight <= scroller.clientHeight + 2) return;
    page.classList.add('book-density-compact');
    void scroller.offsetHeight;
    if (scroller.scrollHeight <= scroller.clientHeight + 2) return;
    page.classList.add('book-density-tight');
    void scroller.offsetHeight;
    page.classList.toggle('is-book-overflowing', scroller.scrollHeight > scroller.clientHeight + 2);
  }

  function fitCoverTitle() {
    var cover = reader.querySelector('.book-cover');
    var copy = cover && cover.querySelector('.book-cover-copy');
    var title = copy && copy.querySelector('h1');
    if (!copy || !title) return;

    title.style.removeProperty('font-size');
    var copyStyle = window.getComputedStyle(copy);
    var availableHeight = copy.clientHeight -
      (parseFloat(copyStyle.paddingTop) || 0) -
      (parseFloat(copyStyle.paddingBottom) || 0);
    var fontSize = parseFloat(window.getComputedStyle(title).fontSize) || 48;
    var minimum = window.innerWidth <= 420 || window.innerHeight <= 500 ? 24 : 32;

    while (title.scrollHeight > availableHeight + 1 && fontSize > minimum) {
      fontSize = Math.max(minimum, fontSize - 2);
      title.style.fontSize = fontSize + 'px';
    }

    cover.classList.toggle('is-title-fitted', title.hasAttribute('style'));
  }

  function renderMermaids(pageList) {
    var rawHosts = [];
    pageList.forEach(function (page) {
      page.querySelectorAll('[data-book-mermaid-index]').forEach(function (node) {
        rawHosts.push(node);
      });
    });
    if (!rawHosts.length) return;

    if (!window.mermaid || typeof window.mermaid.render !== 'function') {
      window.setTimeout(function () { renderMermaids(pageList); }, 120);
      return;
    }

    if (document.fonts && document.fonts.status !== 'loaded') {
      document.fonts.ready.then(function () { renderMermaids(pageList); });
      return;
    }

    if (!mermaidConfigured && typeof window.mermaid.initialize === 'function') {
      window.mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'loose',
        theme: 'base',
        themeVariables: {
          fontFamily: 'SUIT, sans-serif',
          fontSize: '18px'
        },
        flowchart: {
          htmlLabels: true,
          nodeSpacing: 28,
          rankSpacing: 42,
          curve: 'basis'
        }
      });
      mermaidConfigured = true;
    }

    rawHosts.forEach(function (rawHost) {
      var sourceIndex = parseInt(rawHost.getAttribute('data-book-mermaid-index'), 10);
      if (isNaN(sourceIndex) || !mermaidSources[sourceIndex]) return;

      var host = rawHost;
      if (!rawHost.classList.contains('mermaid')) {
        host = document.createElement('div');
        host.className = 'mermaid';
        host.setAttribute('data-book-mermaid-index', String(sourceIndex));
        rawHost.replaceWith(host);
      }
      if (
        host.getAttribute('data-book-mermaid-ready') === 'true' ||
        host.getAttribute('data-book-mermaid-rendering') === 'true'
      ) return;

      host.setAttribute('data-book-mermaid-rendering', 'true');
      host.textContent = '';
      mermaidRenderSequence += 1;
      var renderId = 'book-mermaid-' + sourceIndex + '-' + mermaidRenderSequence;

      Promise.resolve(window.mermaid.render(renderId, mermaidSources[sourceIndex]))
        .then(function (result) {
          var svgMarkup = typeof result === 'string' ? result : result && result.svg;
          if (!svgMarkup) throw new Error('Mermaid returned no SVG');
          host.innerHTML = svgMarkup;
          var svg = host.querySelector('svg');
          if (svg) {
            svg.removeAttribute('height');
            svg.setAttribute('width', '100%');
            svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
          }
          if (result && typeof result.bindFunctions === 'function') result.bindFunctions(host);
          host.setAttribute('data-book-mermaid-ready', 'true');
          host.removeAttribute('data-book-mermaid-index');
          host.setAttribute('role', 'img');
          host.setAttribute(
            'aria-label',
            (host.closest('[data-book-page]').getAttribute('data-book-label') || '본문') + ' 도식'
          );
        })
        .catch(function (error) {
          host.classList.add('book-diagram-fallback');
          host.textContent = mermaidSources[sourceIndex];
          if (window.console) console.error('book mermaid render failed:', error);
        })
        .finally(function () {
          host.removeAttribute('data-book-mermaid-rendering');
          window.requestAnimationFrame(function () {
            fitPageToViewport(host.closest('[data-book-page]'));
          });
        });
    });
  }

  function usesSpread() {
    return !!(spreadMedia && spreadMedia.matches && !scrollView);
  }

  function paginationKey() {
    return [
      window.innerWidth < 768 ? 'mobile' : 'wide',
      window.innerHeight <= 650 ? 'short' : 'tall'
    ].join('-');
  }

  function spreadBounds(index) {
    var bounded = Math.max(0, Math.min(index, pages.length - 1));
    var finishIndex = pages.length - 1;

    if (!usesSpread() || bounded === 0 || bounded === finishIndex) {
      return { start: bounded, end: bounded };
    }

    var start = 1 + Math.floor((bounded - 1) / 2) * 2;
    return { start: start, end: Math.min(start + 1, finishIndex - 1) };
  }

  function updateHash(index, anchorId) {
    if (!window.history || typeof window.history.replaceState !== 'function') return;
    var url = new URL(window.location.href);
    url.searchParams.delete('view');
    url.hash = anchorId ? encodeURIComponent(anchorId) : 'book-page-' + (index + 1);
    window.history.replaceState({ bookPage: index }, '', url.pathname + url.search + url.hash);
  }

  function announce(index, bounds) {
    if (!announcer) return;
    var pageRange = bounds.end > bounds.start
      ? pad(bounds.start + 1) + '–' + pad(bounds.end + 1)
      : pad(index + 1);
    var labels = [];
    for (var pageIndex = bounds.start; pageIndex <= bounds.end; pageIndex += 1) {
      labels.push(pages[pageIndex].getAttribute('data-book-label'));
    }
    announcer.textContent = pageRange + '/' + pad(pages.length) + '쪽, ' + labels.join(', ');
  }

  function updateTocCurrent(index, bounds) {
    if (!tocList) return;
    bounds = bounds || spreadBounds(index);
    tocList.querySelectorAll('[data-book-goto]').forEach(function (button) {
      var buttonIndex = parseInt(button.getAttribute('data-book-goto'), 10);
      var isCurrent = buttonIndex >= bounds.start && buttonIndex <= bounds.end;
      button.classList.toggle('is-current', isCurrent);
      if (buttonIndex === index) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
  }

  function setPageVisibility(index) {
    var bounds = spreadBounds(index);
    var spread = usesSpread() && bounds.end > bounds.start;
    var unpaired = usesSpread() && bounds.start === bounds.end && bounds.start > 0 && bounds.end < pages.length - 1;
    reader.classList.toggle('is-spread', usesSpread());
    reader.classList.toggle('has-open-spread', spread);
    reader.classList.toggle('has-unpaired-page', unpaired);
    reader.classList.toggle('is-cover-open', bounds.start === 0);

    pages.forEach(function (page, pageIndex) {
      var visible = pageIndex >= bounds.start && pageIndex <= bounds.end;
      page.classList.toggle('is-active', visible);
      page.classList.toggle('is-spread-left', spread && pageIndex === bounds.start);
      page.classList.toggle('is-spread-right', spread && pageIndex === bounds.end);
      page.classList.toggle('is-spread-solo', !spread && visible);
      page.setAttribute('aria-hidden', visible ? 'false' : 'true');
      if (visible) page.removeAttribute('hidden');
      else page.setAttribute('hidden', 'until-found');
      page.querySelectorAll('video').forEach(function (video) {
        if (visible && !reduceMotion && video.hasAttribute('autoplay')) {
          var playback = video.play();
          if (playback && typeof playback.catch === 'function') playback.catch(function () {});
        } else {
          video.pause();
        }
      });
    });

    return bounds;
  }

  function pageScroller(page) {
    return page && page.querySelector('.book-page-scroll');
  }

  function scrollToAnchor(target, page) {
    if (!target) return;
    window.requestAnimationFrame(function () {
      var scroller = pageScroller(page);
      if (scroller && scroller.scrollHeight > scroller.clientHeight) {
        var top = target.getBoundingClientRect().top - scroller.getBoundingClientRect().top + scroller.scrollTop - 24;
        scroller.scrollTo({ top: Math.max(0, top), behavior: reduceMotion ? 'auto' : 'smooth' });
      } else {
        target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
      }
    });
  }

  function showPage(index, options) {
    options = options || {};
    if (scrollView || !pages.length) return;

    var nextIndex = Math.max(0, Math.min(index, pages.length - 1));
    var oldIndex = currentIndex;
    var direction = nextIndex >= oldIndex ? 'forward' : 'back';
    var page = pages[nextIndex];

    currentIndex = nextIndex;
    var bounds = setPageVisibility(nextIndex);
    var visiblePages = pages.slice(bounds.start, bounds.end + 1);

    pages.forEach(function (bookPage) {
      bookPage.classList.remove('is-entering-forward', 'is-entering-back');
    });
    if (nextIndex !== oldIndex && !reduceMotion) {
      void page.offsetWidth;
      visiblePages.forEach(function (bookPage) {
        bookPage.classList.add(direction === 'forward' ? 'is-entering-forward' : 'is-entering-back');
      });
    }

    visiblePages.forEach(function (bookPage) {
      var scroller = pageScroller(bookPage);
      if (scroller && (!options.anchor || bookPage !== page)) scroller.scrollTop = 0;
    });

    previousButton.disabled = bounds.start === 0;
    nextButton.disabled = bounds.end === pages.length - 1;
    currentNode.textContent = bounds.end > bounds.start
      ? pad(bounds.start + 1) + '–' + pad(bounds.end + 1)
      : pad(nextIndex + 1);
    totalNode.textContent = pad(pages.length);
    currentLabel.textContent = visiblePages.map(function (bookPage) {
      return bookPage.getAttribute('data-book-label');
    }).join(' / ');
    progressBar.style.width = (pages.length <= 1 ? 100 : (bounds.end / (pages.length - 1)) * 100) + '%';
    updateTocCurrent(nextIndex, bounds);
    announce(nextIndex, bounds);
    resizeVisuals(visiblePages);
    syncAfterword(bounds.end === pages.length - 1);

    if (bounds.start > 0 && bounds.end < pages.length - 1) safeStorageSet(bounds.start);
    if (nextIndex === pages.length - 1) {
      safeStorageSet('complete');
      if (options.track !== false) track('book_complete', { page_count: pages.length });
    } else if (options.track !== false) {
      visiblePages.forEach(function (bookPage, offset) {
        var pageIndex = bounds.start + offset;
        if (viewedPages[pageIndex]) return;
        viewedPages[pageIndex] = true;
        track('book_page_view', {
          page_number: pageIndex + 1,
          page_count: pages.length,
          chapter_title: bookPage.getAttribute('data-book-label'),
          view_mode: usesSpread() ? 'spread' : 'page'
        });
      });
    }

    if (options.updateHash !== false) updateHash(nextIndex, options.anchor && options.anchor.id);
    if (options.anchor) scrollToAnchor(options.anchor, page);

    if (options.focus) {
      window.requestAnimationFrame(function () {
        page.focus({ preventScroll: true });
      });
    }

    if (
      options.scrollTop !== false &&
      window.matchMedia &&
      window.matchMedia('(max-width: 767.98px)').matches
    ) {
      reader.querySelector('.book-reader-shell').scrollIntoView({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: 'start'
      });
    }
  }

  function nextPage() {
    var bounds = spreadBounds(currentIndex);
    if (bounds.end < pages.length - 1) showPage(bounds.end + 1, { focus: true });
  }

  function previousPage() {
    var bounds = spreadBounds(currentIndex);
    if (bounds.start > 0) showPage(bounds.start - 1, { focus: true });
  }

  function setScrollView(enabled, options) {
    options = options || {};
    if (!enabled && paginationKey() !== initialPaginationKey) {
      window.location.reload();
      return;
    }
    scrollView = !!enabled;
    document.body.classList.toggle('book-scroll-view-open', scrollView);
    reader.classList.toggle('is-scroll-view', scrollView);
    if (scrollView) reader.classList.remove('is-spread', 'has-open-spread', 'has-unpaired-page');
    viewButton.setAttribute('aria-pressed', scrollView ? 'true' : 'false');
    viewButton.querySelector('i').className = scrollView ? 'fa-solid fa-book-open' : 'fa-solid fa-align-left';
    viewButton.querySelector('span').textContent = scrollView ? '페이지 보기' : '스크롤 보기';

    if (scrollView) {
      ensureScrollAd();
      pages.forEach(function (page) {
        page.removeAttribute('hidden');
        page.removeAttribute('aria-hidden');
      });
      syncAfterword(true);
      resizeVisuals(pages);
    } else {
      var bounds = setPageVisibility(currentIndex);
      syncAfterword(bounds.end === pages.length - 1);
      resizeVisuals(pages.slice(bounds.start, bounds.end + 1));
    }

    if (window.history && typeof window.history.replaceState === 'function') {
      var url = new URL(window.location.href);
      if (scrollView) {
        url.searchParams.set('view', 'scroll');
        url.hash = '';
      } else {
        url.searchParams.delete('view');
        url.hash = 'book-page-' + (currentIndex + 1);
      }
      window.history.replaceState(
        { bookPage: currentIndex, scrollView: scrollView },
        '',
        url.pathname + url.search + url.hash
      );
    }

    if (!options.silent) {
      track('book_view_change', { view_mode: scrollView ? 'scroll' : 'pages' });
      reader.querySelector('.book-reader-shell').scrollIntoView({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: 'start'
      });
    }
  }

  function ignoredNavigationTarget(target) {
    return !!(
      target.closest(
        'input, textarea, select, button, a, summary, details, video, audio, [contenteditable="true"], pre, code, .table-wrapper, .mermaid, .chartjs-wrap'
      ) || (window.getSelection && String(window.getSelection()).length)
    );
  }

  function wireFaqs() {
    reader.querySelectorAll('details.book-faq-item').forEach(function (details) {
      details.addEventListener('toggle', function () {
        var page = details.closest('[data-book-page]');
        if (details.open && page) {
          page.querySelectorAll('details.book-faq-item[open]').forEach(function (other) {
            if (other !== details) other.open = false;
          });
        }
        window.setTimeout(function () {
          if (page) fitPageToViewport(page);
        }, 0);
      });
    });
  }

  function handleKeyboard(event) {
    if (scrollView || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
    if (ignoredNavigationTarget(event.target)) return;

    var scroller = pageScroller(pages[currentIndex]);
    var atTop = !scroller || scroller.scrollTop <= 4;
    var atBottom = !scroller || scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 4;

    if (event.key === 'ArrowRight' || (event.key === 'PageDown' && atBottom)) {
      event.preventDefault();
      nextPage();
    } else if (event.key === 'ArrowLeft' || (event.key === 'PageUp' && atTop)) {
      event.preventDefault();
      previousPage();
    } else if (event.key === 'Home' && event.shiftKey) {
      event.preventDefault();
      showPage(0, { focus: true });
    } else if (event.key === 'End' && event.shiftKey) {
      event.preventDefault();
      showPage(pages.length - 1, { focus: true });
    }
  }

  function findPageForElement(element) {
    var page = element && element.closest('[data-book-page]');
    return page ? pages.indexOf(page) : -1;
  }

  function initialPageFromUrl() {
    var hash = window.location.hash.replace(/^#/, '');
    if (!hash) return 0;

    var pageMatch = hash.match(/^book-page-(\d+)$/);
    if (pageMatch) return Math.max(0, Math.min(parseInt(pageMatch[1], 10) - 1, pages.length - 1));

    try {
      var target = document.getElementById(decodeURIComponent(hash));
      var index = findPageForElement(target);
      if (index >= 0) return index;
    } catch (_) {
      return 0;
    }
    return 0;
  }

  function initialAnchorFromUrl() {
    var hash = window.location.hash.replace(/^#/, '');
    if (!hash || /^book-page-\d+$/.test(hash)) return null;
    try {
      return document.getElementById(decodeURIComponent(hash));
    } catch (_) {
      return null;
    }
  }

  function handleAnchorClick(event) {
    var link = event.target.closest('a[href*="#"]');
    if (!link || !reader.contains(link)) return;
    var url;
    try {
      url = new URL(link.href, window.location.href);
    } catch (_) {
      return;
    }
    if (url.pathname !== window.location.pathname || !url.hash) return;

    var target;
    try {
      target = document.getElementById(decodeURIComponent(url.hash.slice(1)));
    } catch (_) {
      return;
    }
    var index = findPageForElement(target);
    if (index < 0) return;

    event.preventDefault();
    if (scrollView) {
      currentIndex = index;
      target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
      updateTocCurrent(index);
    } else {
      showPage(index, { anchor: target, focus: false });
    }
  }

  function updateThemeButton() {
    if (!themeButton) return;
    var dark = window.Theme
      ? window.Theme.isDark
      : document.documentElement.getAttribute('data-bs-theme') === 'dark';
    var icon = themeButton.querySelector('i');
    icon.className = dark ? 'fa-regular fa-sun' : 'fa-regular fa-moon';
    themeButton.setAttribute('aria-label', dark ? '밝은 화면으로 전환' : '어두운 화면으로 전환');
  }

  function toggleTheme() {
    if (window.Theme && window.Theme.isToggleable) {
      window.Theme.update(window.Theme.isDark ? window.Theme.Mode.LIGHT : window.Theme.Mode.DARK);
    } else {
      var html = document.documentElement;
      var dark = html.getAttribute('data-bs-theme') === 'dark';
      html.setAttribute('data-bs-theme', dark ? 'light' : 'dark');
    }
    window.setTimeout(function () {
      updateThemeButton();
      resizeVisuals(pages[currentIndex]);
    }, 40);
  }

  function shareBook() {
    var page = pages[currentIndex];
    var heading = page.querySelector('h2[id]');
    var url = new URL(window.location.href);
    url.searchParams.delete('view');
    url.hash = heading ? heading.id : 'book-page-' + (currentIndex + 1);
    var data = {
      title: reader.getAttribute('data-book-title') || document.title,
      text: page.getAttribute('data-book-label'),
      url: url.toString()
    };

    if (navigator.share) {
      navigator.share(data).then(function () {
        track('book_share', { share_method: 'native' });
      }).catch(function () {});
      return;
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(data.url).then(function () {
        var original = shareButton.innerHTML;
        shareButton.textContent = '링크를 복사했습니다';
        if (announcer) announcer.textContent = '공유 링크를 복사했습니다.';
        track('book_share', { share_method: 'clipboard' });
        window.setTimeout(function () {
          shareButton.innerHTML = original;
        }, 1800);
      });
    }
  }

  function openToc() {
    if (!tocDialog) return;
    if (typeof tocDialog.showModal === 'function') tocDialog.showModal();
    else tocDialog.setAttribute('open', '');
    var active = tocList && tocList.querySelector('.is-current');
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  function closeToc() {
    if (!tocDialog) return;
    if (typeof tocDialog.close === 'function') tocDialog.close();
    else tocDialog.removeAttribute('open');
  }

  function wireEvents() {
    previousButton.addEventListener('click', previousPage);
    nextButton.addEventListener('click', nextPage);

    if (startButton) {
      startButton.addEventListener('click', function () {
        var saved = parseInt(startButton.getAttribute('data-resume-page'), 10);
        showPage(!isNaN(saved) ? saved : 1, { focus: true });
      });
    }

    restartButton.addEventListener('click', function () {
      safeStorageSet(0);
      showPage(0, { focus: true });
    });

    viewButton.addEventListener('click', function () {
      setScrollView(!scrollView);
    });
    themeButton.addEventListener('click', toggleTheme);
    if (shareButton) shareButton.addEventListener('click', shareBook);

    if (afterwordButton) {
      afterwordButton.addEventListener('click', openAfterword);
    }

    tocOpen.addEventListener('click', openToc);
    tocClose.addEventListener('click', closeToc);
    tocDialog.addEventListener('click', function (event) {
      if (event.target === tocDialog) closeToc();
    });
    tocList.addEventListener('click', function (event) {
      var button = event.target.closest('[data-book-goto]');
      if (!button) return;
      var index = parseInt(button.getAttribute('data-book-goto'), 10);
      var targetPage = pages[index];
      var heading = targetPage.querySelector('h2[id]');
      closeToc();

      if (scrollView) {
        currentIndex = index;
        updateTocCurrent(index);
        (heading || targetPage).scrollIntoView({
          behavior: reduceMotion ? 'auto' : 'smooth',
          block: 'start'
        });
      } else {
        showPage(index, { focus: true, anchor: heading || null });
      }
    });

    document.addEventListener('keydown', handleKeyboard);
    reader.addEventListener('click', handleAnchorClick);

    stage.addEventListener('pointerdown', function (event) {
      if (scrollView || event.pointerType === 'mouse' || ignoredNavigationTarget(event.target)) return;
      pointerStart = { x: event.clientX, y: event.clientY, id: event.pointerId };
    });

    stage.addEventListener('pointerup', function (event) {
      if (!pointerStart || pointerStart.id !== event.pointerId) return;
      var deltaX = event.clientX - pointerStart.x;
      var deltaY = event.clientY - pointerStart.y;
      pointerStart = null;
      if (Math.abs(deltaX) < 48 || Math.abs(deltaX) < Math.abs(deltaY) * 1.25) return;
      if (deltaX < 0) nextPage();
      else previousPage();
    });

    stage.addEventListener('click', function (event) {
      if (scrollView || ignoredNavigationTarget(event.target)) return;
      if (event.detail === 0) return;
      var bounds = stage.getBoundingClientRect();
      if (event.clientX < bounds.left + bounds.width * 0.32) previousPage();
      else if (event.clientX > bounds.left + bounds.width * 0.68) nextPage();
    });

    window.addEventListener('hashchange', function () {
      if (scrollView) return;
      var index = initialPageFromUrl();
      if (index !== currentIndex) showPage(index, { updateHash: false, focus: false });
    });

    window.addEventListener('resize', function () {
      window.clearTimeout(viewportResizeTimer);
      viewportResizeTimer = window.setTimeout(function () {
        if (document.body.classList.contains('book-afterword-open')) return;
        if (paginationKey() !== initialPaginationKey) {
          if (!scrollView) window.location.reload();
          return;
        }

        fitCoverTitle();

        if (scrollView) {
          resizeVisuals(pages);
          return;
        }

        showPage(currentIndex, {
          updateHash: false,
          focus: false,
          scrollTop: false,
          track: false
        });
      }, 180);
    });

    if (spreadMedia) {
      var refreshSpread = function () {
        if (scrollView) return;
        showPage(currentIndex, {
          updateHash: false,
          focus: false,
          scrollTop: false,
          track: false
        });
      };
      if (typeof spreadMedia.addEventListener === 'function') {
        spreadMedia.addEventListener('change', refreshSpread);
      } else if (typeof spreadMedia.addListener === 'function') {
        spreadMedia.addListener(refreshSpread);
      }
    }

    window.addEventListener('message', function (event) {
      if (window.Theme && event.data && event.data.id === window.Theme.eventId) {
        window.setTimeout(updateThemeButton, 20);
      }
    });
  }

  function init() {
    if (reader.classList.contains('is-ready')) {
      clearFallbackTimer();
      return;
    }
    if (pages.length < 2) {
      failOpen();
      return;
    }

    buildSourceButtons();
    paginateContent();
    labelPages();
    decoratePages();
    wireFaqs();
    buildToc();
    wireEvents();
    updateThemeButton();

    var savedValue = safeStorageGet();
    var savedPage = parseInt(savedValue, 10);
    if (startButton && startLabel && !isNaN(savedPage) && savedPage > 0 && savedPage < pages.length - 1) {
      startButton.setAttribute('data-resume-page', String(savedPage));
      startLabel.textContent = pad(savedPage + 1) + '쪽부터 계속 읽기';
    }

    reader.classList.add('is-ready');
    clearFallbackTimer();
    fitCoverTitle();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitCoverTitle);
    var requestedScrollView = new URL(window.location.href).searchParams.get('view') === 'scroll';
    var initialAnchor = initialAnchorFromUrl();
    currentIndex = initialPageFromUrl();

    if (requestedScrollView) {
      setScrollView(true, { silent: true });
      currentNode.textContent = pad(currentIndex + 1);
      totalNode.textContent = pad(pages.length);
      currentLabel.textContent = pages[currentIndex].getAttribute('data-book-label');
      updateTocCurrent(currentIndex);
    } else {
      showPage(currentIndex, {
        updateHash: false,
        focus: false,
        scrollTop: false,
        anchor: initialAnchor
      });
    }

    track('book_open', {
      page_count: pages.length,
      chapter_count: parseInt(reader.getAttribute('data-book-chapters'), 10) || pages.length - 2,
      view_mode: requestedScrollView ? 'scroll' : 'pages'
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      window.setTimeout(init, 180);
    });
  } else {
    window.setTimeout(init, 180);
  }
})();

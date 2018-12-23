dofile("table_show.lua")
dofile("urlcode.lua")

local item_type = os.getenv('item_type')
local item_value = string.gsub(os.getenv('item_value'), "%-", "%%-")
local item_dir = os.getenv('item_dir')
local warc_file_base = os.getenv('warc_file_base')

local ids = {}

local url_count = 0
local tries = 0
local downloaded = {}
local addedtolist = {}
local abortgrab = false

-- Tumblr seem to be using epoch time on the /archive endpoint
-- Goal: Get more posts, using epoch minus time in seconds for each month
local epochtime = 1543953699
local epochpermonth = 2629743
local concat = "^https?://".. item_value .. "%.tumblr%.com/?[^/]*/?[^/]*/?[^/]*/?[^/]*/?[^/]*$"
local video = "^https?://www%.tumblr%.com/video/".. item_value .. "/?.*/?.*/?.*"

local discovered_blogs = {}

local media_file = io.open(item_dir..'/'..warc_file_base..'_media.txt', 'w')

for ignore in io.open("ignore-list", "r"):lines() do
  downloaded[ignore] = true
end

read_file = function(file)
  if file then
    local f = assert(io.open(file))
    local data = f:read("*all")
    f:close()
    return data
  else
    return ""
  end
end

should_add_media = function(url, parenturl)
  if string.match(url, video) 
  or string.match(url, "vtt%.tumblr%.com")
  then
    return true
  end
  
  if string.match(url, "^https?://assets%.tumblr%.com")
  or string.match(url, "^https?://static%.tumblr%.com")
  or string.match(url, "^https?://[0-9]+%.media%.tumblr%.com")
  then
    if parenturl ~= nil then
      if string.match(parenturl, concat) then
        return true
      end
    else
      return true
    end
  end
  
  if string.match(url, "^https?://[a-z]+%.media%.tumblr%.com") then
    if parenturl ~= nil then
      if string.match(parenturl, "^https?://www%.tumblr%.com") then
        return true
      end
    else
      return true
    end
  end
  
  return false
end

allowed = function(url, parenturl)
  if string.match(url, "'+")
  or string.match(url, "[<>\\%*%$;%^%[%],%(%)]")
  or string.match(url, "//$")
  or string.match(url, "^https?://ns%.adobe%.com")
  or string.match(url, "^https?://www%.change%.org")
  or string.match(url, "^https?://[^.]+/") 
  or string.match(url, "^https?://radar%.cedexis%.com")
  or string.match(url, "^https?://[0-9]+%.media%.tumblr%.com/%p+%d+")
  or string.match(url, "^https?://assets%.tumblr%.com/%p+%d+")
  or string.match(url, "^https?://static%.tumblr%.com/%p+%d+")
  or string.match(url, "^https?://[0-9]+%.media%.tumblr%.com/avatar_[a-zA-Z0-9]+_%d%d%.[pjg][npi][jgf]$")
  or string.match(url, "^https?://[0-9]+%.media%.tumblr%.com/post/")
  or string.match(url, "^https?://assets%.tumblr%.com/archive")
  or string.match(url, "^https?://assets%.tumblr%.com/filter%-by")
  or string.match(url, "^https?://assets%.tumblr%.com/client")
  or string.match(url, "^https?://static%.tumblr%.com/[%u%p%l]+")
  or string.match(url, "ios%-app://")
  or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/notes")
  or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/post/%d+/amp$")
  or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/post/%d+/embed$")
  or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/post/%d+/[^/]+/amp$")
  or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/post/%d+/[^/]+/embed$")
  or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/post/%d+/embed$")
  or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/rss$")
  or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/reblog")
  or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/.*%?route=")
 -- or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/likes/page/%d%d%d")
  or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/[^/]+%%")
  --[[
  exclude /: template urls when discovering urls because for some reason wget-lua 
  does not properly call download_child(_p) when deciding whether to download these
  ]]
  or string.find(url, "/:year")
  or string.find(url, "/:month")
  or string.find(url, "/:id")
  or string.find(url, "/:page")
  or string.find(url, "/:blog_not_found")
  or string.find(url, "/:tag")
  then
    return false
  end

  if string.match(url, "^https?://[^%.]+%.tumblr%.com") then
    local blogname = string.match(url, "^https?://([^%.]+)%.tumblr%.com")
    if blogname ~= item_value then
      discovered_blogs[blogname] = true
    end
  end
  
  if string.match(url, concat) then
    if parenturl ~= nil then
      if string.match(parenturl, concat) or string.match(url, "^https?://www%.tumblr%.com/") then
        return true
      else
        return false
      end
    end
    return true
  end
  
  if should_add_media(url, parenturl) then
    media_file:write(url .. "\n")
    return false
  end
  
  return false
end

wget.callbacks.download_child_p = function(urlpos, parent, depth, start_url_parsed, iri, verdict, reason)
  local url = urlpos["url"]["url"]
  local html = urlpos["link_expect_html"]
 
  if string.find(url, "code%.jquery%.com") then
    -- Ignore code.jquery.com
    return false
  end
  
  if string.find(url, "fonts%.googleapis%.com") then
    -- Ignore fonts.googleapis.com
    return false
  end
  
  if string.find(url, "px.srvcs.tumblr.com") then
    -- Ignore px.srvcs.tumblr.com tracking domain
    return false
  end

  if string.find(url, "/:year")
  or string.find(url, "/:month")
  or string.find(url, "/:id")
  or string.find(url, "/:page")
  or string.find(url, "/:blog_not_found")
  or string.find(url, "/:tag")
  then 
    return false
  end

  if string.match(url, "^https?://www.tumblr.com/oembed/1.0")
  or string.match(url, "^https?://" .. item_value .. "%.tumblr%.com/post/%d+/[^/]+/embed$")
  or string.match(url, "^https?://[0-9]+%.media%.tumblr%.com/avatar_[a-zA-Z0-9]+_%d%d%.[pjg][npi][jgf]$") then
    -- Ignore small avatars (16x16 and 64x64)
    return false
  end
  
  if (downloaded[url] ~= true and addedtolist[url] ~= true)
  and (allowed(url, parent["url"]) or html == 0)
  then
    if should_add_media(url, parent["url"]) then
      -- already added to media list in allowed, don't need to add it again,
      -- but must return false here
      return false
    end
    addedtolist[url] = true
    return true
  end
  
  return false
end

wget.callbacks.get_urls = function(file, url, is_css, iri)
  local urls = {}
  local html = nil
  
  downloaded[url] = true
  local function check(urla)
    local origurl = url
    local url = string.match(urla, "^([^#]+)")
    local url_ = string.gsub(url, "&amp;", "&")
    if (downloaded[url_] ~= true and addedtolist[url_] ~= true)
       and allowed(url_, origurl) then
      table.insert(urls, { url=url_ })
      addedtolist[url_] = true
      addedtolist[url] = true
    end
  end
  local function checknewurl(newurl)
    if string.match(newurl, "^https?:////") then
      check(string.gsub(newurl, ":////", "://"))
    elseif string.match(newurl, "^https?://") then
      check(newurl)
    elseif string.match(newurl, "^https?:\\/\\?/") then
      check(string.gsub(newurl, "\\", ""))
    elseif string.match(newurl, "^\\/\\/") then
      check(string.match(url, "^(https?:)")..string.gsub(newurl, "\\", ""))
    elseif string.match(newurl, "^//") then
      check(string.match(url, "^(https?:)")..newurl)
    elseif string.match(newurl, "^\\/") then
      check(string.match(url, "^(https?://[^/]+)")..string.gsub(newurl, "\\", ""))
    elseif string.match(newurl, "^/") then
      check(string.match(url, "^(https?://[^/]+)")..newurl)
    end
  end
  local function checknewshorturl(newurl)
    if string.match(newurl, "^%?") then
      check(string.match(url, "^(https?://[^%?]+)")..newurl)
    elseif not (string.match(newurl, "^https?:\\?/\\?//?/?")
       or string.match(newurl, "^[/\\]")
       or string.match(newurl, "^[jJ]ava[sS]cript:")
       or string.match(newurl, "^[mM]ail[tT]o:")
       or string.match(newurl, "^vine:")
       or string.match(newurl, "^android%-app:")
       or string.match(newurl, "^%${")) then
      check(string.match(url, "^(https?://.+/)")..newurl)
    end
  end
  if not (string.match(url, "^https?://[0-9a-z]+%.media%.tumblr%.com")
          or string.match(url, "^https?://vtt%.tumblr%.com"))
  and allowed(url, nil) then
    html = read_file(file)
    if string.match(html, '<title>Request denied%.</title>') then
      abortgrab = true
      return urls
    end
    for newurl in string.gmatch(html, '([^"]+)') do
      checknewurl(newurl)
    end
    for newurl in string.gmatch(html, "([^']+)") do
      checknewurl(newurl)
    end
    for newurl in string.gmatch(html, ">%s*([^<%s]+)") do
       checknewurl(newurl)
    end
    for newurl in string.gmatch(html, "[^%-]href='([^']+)'") do
      checknewshorturl(newurl)
    end
    for newurl in string.gmatch(html, '[^%-]href="([^"]+)"') do
      checknewshorturl(newurl)
    end
    for newurl in string.gmatch(html, ":%s*url%(([^%)]+)%)") do
      check(newurl)
    end
  end

  return urls
end

wget.callbacks.httploop_result = function(url, err, http_stat)
  status_code = http_stat["statcode"]
  
  url_count = url_count + 1
  io.stdout:write(url_count .. "=" .. status_code .. " " .. url["url"] .. "  \n")
  io.stdout:flush()

  if (status_code >= 300 and status_code <= 399) then
    local newloc = http_stat["newloc"]
    if string.match(newloc, "https?://www%.tumblr%.com/privacy/consent") then
      return wget.actions.ABORT
    end
    if string.match(newloc, "https?://www%.tumblr%.com/safe%-mode") then
      if string.match(url["url"], "^https?://" .. item_value .. "%.tumblr%.com/$") then -- abort this item if we encounter a redirect to safe-mode already at the beginning
        return wget.actions.ABORT
      end
      return wget.actions.EXIT
    end
  end
  
  if (status_code >= 200 and status_code <= 399) then
    downloaded[url["url"]] = true
    downloaded[string.gsub(url["url"], "https?://", "http://")] = true
  end

  if abortgrab == true then
    io.stdout:write("ABORTING...\n")
    return wget.actions.ABORT
  end
  
  if status_code >= 500
  or (status_code > 400 and status_code < 403 and status_code ~= 404)
  or status_code > 404
  then
    io.stdout:write("Server returned "..http_stat.statcode.." ("..err.."). Sleeping.\n")
    io.stdout:flush()
    local maxtries = 10 -- default: bail out after 10 retires or 2047 seconds (2^11 or 1+2+4+8+16+32+64+128+256+512+1024)
    if string.match(url["url"], "_%d+.[pjg][npi][ggf]$")
    or string.match(url["url"], "%.[pjg][npi][ggf]$")
    then
      maxtries = 8 -- we don't care that much about errors on media urls and skip those earlier: after 255 seconds (2^8 or 1+2+4+8+16+32+64+128)
    end
    if tries > maxtries then
      io.stdout:write("\nI give up...\n")
      io.stdout:flush()
      tries = 0
      if string.match(url["url"], "_%d+.[pjg][npi][ggf]$")
      or string.match(url["url"], "%.[pjg][npi][ggf]$")
      then
        return wget.actions.EXIT -- just skip this url instead of aborting the entire item when we hit a bad media url
      end
      if allowed(url["url"], nil) then
        return wget.actions.ABORT
      else
        return wget.actions.EXIT
      end
    else
      local backoff = math.floor(math.pow(2, tries)) -- math.pow returns a float, math.floor turns it into an int so the sleep cmd gets an int
      os.execute("sleep " .. backoff)
      tries = tries + 1
      return wget.actions.CONTINUE
    end
  end
  
  if status_code == 403 -- banned
  or status_code == 400 -- ?
  or status_code == 429 -- rate limit exceeded
  or status_code == 0 -- download error
  then
    --if string.match(url["host"], "")
    if string.match(url["host"], "assets%.tumblr%.com")
    or string.match(url["host"], "static%.tumblr%.com")
    or string.match(url["host"], "[a-z0-9]+%.media%.tumblr%.com")
    or string.match(url["host"], "vtt%.tumblr%.com")
    or string.match(url["host"], "www%.tumblr%.com")
    or string.match(url["host"], "counter%.website%-hit%-counters%.com")
    or string.match(url["url"], "^https?://".. item_value .."%.tumblr%.com/services")
    or string.match(url["url"], "%.[pjg][npi][ggf]$") then
      io.stdout:write("Server returned " ..http_stat.statcode.." ("..err.."). Skipping.\n")
      tries = 0
      return wget.actions.EXIT
    else
      io.stdout:write("Server returned " ..http_stat.statcode.." ("..err.."). Sleeping.\n")
      io.stdout:flush()
      if tries > 10 then -- bail out after 10 retries or 2047 seconds (2^11 or 1+2+4+8+16+32+64+128+256+512+1024)
        io.stdout:write("\nI give up...\n")
        io.stdout:flush()
        tries = 0
        if allowed(url["url"], nil) then
          return wget.actions.ABORT
        else
          return wget.actions.EXIT
        end
      else
        local backoff = math.floor(math.pow(2, tries)) -- math.pow returns a float, math.floor turns it into an int so the sleep cmd gets an int
        os.execute("sleep " .. backoff)
        tries = tries + 1
        return wget.actions.CONTINUE
      end
    end
  end

  tries = 0

  local sleep_time = 0

  if sleep_time > 0.001 then
    os.execute("sleep " .. sleep_time)
  end

  return wget.actions.NOTHING
end

wget.callbacks.finish = function(start_time, end_time, wall_time, numurls, total_downloaded_bytes, total_download_time)
  local file = io.open(item_dir..'/'..warc_file_base..'_data.txt', 'w')
  if item_type == "tumblr-blog" then
    for blog, _ in pairs(discovered_blogs) do
      file:write("tumblr-blog:" .. blog .. "\n")
    end
  end
  file:close()
  media_file:close()
end

wget.callbacks.before_exit = function(exit_status, exit_status_string)
  if abortgrab == true then
    return wget.exits.IO_FAIL
  end
  return exit_status
end

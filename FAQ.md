# Frequently Asked Questions

#### Why was the tracker stopped? Is my warrior going to receive any new work?
- The tracker was stopped because all existing warriors got their IP addresses banned when using the previous crawl script.
  A lot of bad data ("banned" error pages etc.) also got archived upstream on the staging server.
  So until a new script was formed and proven itself and the bad data was pruned from the tracker,
  the tracker was paused so as to not cause any more problems.
- The tracker has been resumed.
  
#### What is the Archive Team currently doing?
 - Working on Frontend (Warrior Queue) and new crawlers.
 - Also trying to get more IPs to circumvent bans.
 - Reverse engineering the private APIs to get valid data.

#### Can you save this blog for me?
- We don't have time to hand-pick blogs.
- Please submit the link to ArchiveTeam's [NSFW Tumblr form](https://docs.google.com/forms/d/e/1FAIpQLSdoYnlweKF-5iQ2G0FB9s7pDV_Le61dDU-gMMDsc8CQ50YBjQ/viewform), but we can't guarantee it'll be saved.
- If there's a blog you absolutely want to save, see "How do I do my own personal backup of a tumblr blog?" below.

#### How do I do my own personal backup of a tumblr blog?
 - Python (cross-platform):
   * [__tumblr_backup.py__](https://github.com/bbolli/tumblr-utils/blob/master/tumblr_backup_for_beginners.md)
     can make a local backup of posts (XML default), video, audio and images. Uses APIv2
 - Windows:
   * [__TumblThree__](https://www.jzab.de/content/tumblthree) can archive an entire blog by feeding it an URL, including asks, text posts and reblogs to XML format and can download all images. Downloadable here. Windows only until the dev implements mono support.
 - Web-based exporters/importers:
   * [__Wordpress.com__ importer](https://en.support.wordpress.com/import/import-from-tumblr/) can migrate your entire Tumblr blog to your own Wordpress.com subdomains. This is an easy and cheap solution to let your blog live. Wordpress.com [allows mature content](https://en.support.wordpress.com/mature-content/) but you can [host Wordpress yourself](https://wordpress.org/hosting/) to be in total control, because it's [free and open source software](https://en.wikipedia.org/wiki/Free_and_open-source_software).
   * [__Tumblr__ export](https://tumblr.zendesk.com/hc/en-us/articles/360005118894-Export-your-blog): you can allegedly get all your data in a single ZIP file, but it may or may not be an [open format](https://opendefinition.org/ofd/) usable elsewhere. [Migrating to Mastodon](https://blog.joinmastodon.org/2018/11/from-tumblr-to-mastodon/) is possible thanks to several independent and nsfw-friendly instances supported by donations but you may need to import the exported data yourself until an [automatica importer](https://github.com/tootsuite/mastodon/issues/9420) is developed.
 - Note that the data produced by these programs is incompatible with Archive Team's format and thus cannot be used by the official project. These are usable for your own backups only.
 
#### Should we submit SFW blogs? after the NSFW are nuked maybe
- Only if you believe their data is at risk.

#### What time/date will the blogs be deleted? 
- Starting 2018-12-17.
- According to some reports, the deletion has already begun.

#### Who got banned? How?
- Every warrior using the official crawl script got their IP address permanently banned sometime around saturday.
- The bans were evidently done by hand and most likely relied on the User-Agent string as well as the excessive access patterns the script caused.
- Everyone got banned, regardless of how much or little they had crawled, and regardless of whether they used a residential or a datacenter IP.

#### Can I run my own crawler and have it appear in the Wayback Machine or Internet Archive?
- Yes, use the official warrior from [#tumbledown on EFnet](http://chat.efnet.org:9090/?channels=%23tumbledown) (IRC).
- Just ask where to find it there.

#### Follow up: I already have a HDD full of data, what should I do with it?
- If it's from an uncompleted warrior job, delete it.
- If not, come to [#tumbledown on EFnet](http://chat.efnet.org:9090/?channels=%23tumbledown) (IRC).

#### What methods work for crawling and what don't?
   * Login- and API-based crawling has been reported to still work regardless of the previous IP ban, but API-based crawling is not compatible
     with the Archive Team's objective. You can still do it for yourself, though.
   * Apart from that, if you're banned, only getting a new IP address somehow.
   * If you are on a residential connection, restarting your router *might* assign you a new IP address from your ISP's pool.

#### What does the Archive Team need the most in this project?
- IP addresses from different warriors around the world.
- Every (HTML) crawler will get rate limited quite quickly, so the number of different connections is much more valuable than huge bandwidth if you cannot spread it over multiple IP addresses.

#### Would VPNs help?
- Data integrity is a very high priority for the Archive Team so use of VPNs with the official crawler is discouraged.
- You will be banned from the tracker if we are aware of you using a VPN.

#### Would proxies help?
- ~No~ __NO.__ Open proxies are absolutely the worst offender in shitting on data in transit or just straight up serving you malware.
  Data integrity is a very high priority for the Archive Team so don't use open proxies with the official project.

#### Is there a master list of done/saved tumblr blogs?
- Not yet. If this becomes available, this page will be updated.

#### Some people are still crawling without limit, why can't we do what they're doing?
 - They're running their own test software, that might produce invalid data.
 - Also they're not crawling without limits, Tumblr bans everyone at some point.
 - Coordinated low volume of crawling likely makes Tumblr a lot less trigger-happy.

Other mass crawlers, in use at the moment:
* https://github.com/terorie/tumblr-panic
  Outputs blogs' internal data and media (images, videos and audio)
  However:
  - This is not compatible with the Archive Team's format.
  - You can't view the output in the browser yet.
  - A second script is added later to output HTML.

#### How do I run and monitor multiple warriors?

A small [tumblr-monitor.sh](https://gist.github.com/JustAnotherArchivist/f4617c902626377532692a341794f273) script can give you something more human-readable and specific than your typical `top` or `atop`.

For more advanced monitoring, some ArchiveTeam members have shared their orchestration solutions, for instance Prometheus with [Terraform on DigitalOcean](https://gitlab.com/diggan/archiveteam-infra); see the [Warrior wiki page](https://www.archiveteam.org/index.php?title=Warrior) for more information.

## Overly Technical Details:

#### What about IPv6 /64 round robin?
- There's only three endpoins with IPv6: www.tumblr.com, api.tumblr.com and api-http2.tumblr.com.
- api-http2.tumblr.com can be used for API-based crawling and includes all metadata, but this is not compatible with Archive Team's format.
- To summarize, the format Archive Team uses (full HTML dumps) cannot be reached via IPv6.
- IP bans aren't enforced on CDN URLs.

#### Why is the script using user-agent `<xy>`?
- Primarily because warriors in the EU were receiving a GDPR opt-in page. Using the Googlebot UA avoided this.
- The bans are IP bans, changing the user agent neither helps us avoid them nor lets us bypass them.
- Tumblr treats all bots equally.

#### Follow up, what about rotating random bot UA's?
- Most likely not needed, if Tumblr were banning by UA, it'd happen a lot sooner.
- You can submit PRs though if you want.
- Note: Don't rotate UAs within the same crawl session/machine/IP address, that is highly suspicious behavior and might get your session flagged.

#### Can we use GCP, EC2 etc?
- Absolutely, but their IP addresses could be banned already, so it's a gamble.
- Some of the biggest players that were hit in the first ban wave were using DigitalOcean.
- AWS with elastic IPs seems mostly unexplored so far, also smaller ISPs might fare better than the big ones.
- Please share your experiences on [#tumbledown on EFnet](http://chat.efnet.org:9090/?channels=%23tumbledown).

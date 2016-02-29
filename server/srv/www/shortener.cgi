#!/usr/bin/env groovy  

/**
*@Author Enrique García Orive
*
*/

@Grapes([
    @Grab('org.mariadb.jdbc:mariadb-java-client:1.3.5'),
    @Grab('ch.qos.logback:logback-core:1.0.10'),
    @Grab('ch.qos.logback:logback-classic:1.0.10'),
    @Grab('org.slf4j:slf4j-api:1.7.16'),
    @GrabConfig(systemClassLoader = true)
])

import org.codehaus.groovy.runtime.InvokerHelper
import com.fastcgi.FCGIInterface
import groovy.util.logging.Slf4j
import groovy.xml.MarkupBuilder
import java.security.SecureRandom
import java.math.BigInteger
import groovy.sql.Sql
import org.mariadb.jdbc.Driver

/**
*
* Shortener groovy script. 
* - It takes an URL and tries to make it shorter.
* - Store it in a MariaDB.
* - Generates a response with a link to the URL shortened.
* - It manages all http requests. 
*
*/
@Slf4j
class Shortener extends Script {
    //Just one SecureRandom object is necessary to generate random numbers
    //because this object takes quite time to be generated.
    private SecureRandom random = new SecureRandom()
    
    //Type of Messages to show in the main index response
    enum ErrorRespMsg{
        TOOLONG,
        IMPOSSIBLE,
        BADSHORTCODE,
        WRONG
    }
    
    /**
    * Method that builds index and error responses. It prints
    * the response to the system output because this is how 
    * FCGI works (see the API for mor info). 
    *
    *@param message Enum that identifies the type of message response
    */
    def indexResponse(message = null){
        def writer = new StringWriter()  // html is written here by markup builder
        def markup = new groovy.xml.MarkupBuilder(writer)  // the builder
        markup.html {
            h1 id: "title",  "OSOCO SHORTENER"
            body(id: "main") {
                if(message!=null){
                    switch(message){
                        case ErrorRespMsg.TOOLONG:
                        p{
                            mkp.yield "URL too long. The limit is 2100 characters."
                        }
                        break
                        case ErrorRespMsg.IMPOSSIBLE:
                        p{
                            mkp.yield "I'cant make it shorter ;(" 
                        }
                        break
                        case ErrorRespMsg.BADSHORTCODE:
                        p{
                            mkp.yield "Unknown shortcode ;("
                        }
                        break
                        case ErrorRespMsg.WRONG:
                        p{
                            mkp.yield "Something was wrong!"
                        }
                        break
                    }
                }
                p {
                    mkp.yield "Paste here your URL: "
                }
                form (action: 'shortener.cgi'){
                    input (type: 'text', name: 'url') 
                    input (type: 'submit', value: 'Shorten URL') 
                }
            }
        }
        log.info("html response: \n" + writer)
        System.out.println("Content-type: text/html\r\n")
        System.out.println(writer)
    }
   
   /**
   *Build the response with both url, the original and the shortened  
   *
   *@param url Original URL to be shortened
   *@param urlShortened that has been shortened.
   */
    def shortenerResponse(url,urlShortened){
        def writer = new StringWriter()  // html is written here by markup builder
        def markup = new groovy.xml.MarkupBuilder(writer)  // the builder
        markup.html {
            h1 id: "title",  "OSOCO SHORTENER"
            body(id: "main") {
                p {
                    mkp.yield ("Your URL: ")
                    if (url.length() > 100){
                        a(href:url, url.substring(0,100)+ "...")
                    }else{
                        a(href:url, "${url}")
                    }
                }
                p {
                    mkp.yield ("Your URL shortened: ")
                    a(href:urlShortened, "${urlShortened}")
                }
            }
        }
        log.info("html response: \n" + writer)
        System.out.println("Content-type: text/html\r\n")
        System.out.println(writer)
    }

    /**
    * Main execution
    *
    */
    def run() {
        log.info("Starting shortener process ...")
        def endPoint = 'http://ego.no-ip.org:7777'
        def mariadbname = Class.forName("org.mariadb.jdbc.Driver")
        log.info("mariadbname = " + mariadbname)
        def sql=Sql.newInstance("endPointDB", "userDB", "passDB", "org.mariadb.jdbc.Driver")
        sql.eachRow("select * from Websites"){
            log.info("website = " + it.Website + ", code = " + it.Shortcode)
        }
        def fcgi = new FCGIInterface()
        def writer // html is written here by markup builder
        def markup  // the builder
        int count = 0
        //After the first execution, this will be the scope of the script
        while(fcgi.FCGIaccept()>= 0) {
            try{
                log.info("Request number " + count + "..." )
                count ++
                writer = new StringWriter()  // html is written here by markup builder
                markup = new groovy.xml.MarkupBuilder(writer)  // the builder
                def complete = fcgi.request.params.REQUEST_URI
                log.debug("complete request = " + complete)
                def url
                if(complete.contains('shortener.cgi?url=')){
                    log.info("Shortener lifecycle path")
                    url = complete.substring(complete.indexOf('url=')+4,complete.length())
                    url = java.net.URLDecoder.decode(url, "UTF-8")
                    log.debug("url = " + url)
                    if (url.length()> 2100){
                        indexResponse(ErrorRespMsg.TOOLONG)
                        continue
                    }
                    def urlSelect = sql.firstRow("SELECT * FROM Websites WHERE Website = ?", [url])
                    log.debug("urlSelect = " + urlSelect)
                    def urlShortened
                    if( urlSelect != null ){
                        log.debug("Website already in our system ...")
                        urlShortened = endPoint + '/' + urlSelect.Shortcode
                        def date = new Date()
                        def sqlTimestamp = date.toTimestamp()
                        sql.executeUpdate("UPDATE Websites SET LastVisit= ? WHERE Shortcode=?", [sqlTimestamp.toString(), urlSelect.Shortcode]) 
                    }else{
                        log.debug("URL not in the system. Generating new code and store it ...")
                        def randomId =  new BigInteger(50, random).toString(32)
                        urlShortened = endPoint + '/' + randomId
                        log.debug("urlShortened = " + urlShortened)
                        def date = new Date()
                        def params = [url, randomId]
                        log.debug("params = " + params)
                        sql.execute 'INSERT INTO Websites (Website, Shortcode) values (?, ?)', params
                    }
                    if(url.size() < urlShortened.size()){
                        indexResponse(ErrorRespMsg.IMPOSSIBLE)
                    }else{
                        shortenerResponse(url,urlShortened)
                    }
                }else {
                    log.debug("Index and shortcode lifecycle path")
                    log.debug("complete = " + complete)
                    def reference = '/shortener.cgi/'
                    if (complete.contains(reference) && ! complete.contains('url')) {
                        log.debug("complete length = " + complete.size())
                        if (complete.size() > reference.size()){
                            def shortcode = complete.substring(reference.size())
                            log.debug("shortcode = " + shortcode)
                            def urlSelect = sql.firstRow("SELECT Website FROM Websites WHERE Shortcode = ?", [shortcode])
                            if(urlSelect != null && urlSelect[0] != null){
                                log.debug("urlSelected = " + urlSelect[0])
                                System.out.println("Status: 301 Moved Permanently")
                                if(urlSelect[0].contains('http')){
                                    System.out.println("Location: " + urlSelect[0] + "\r\n")
                                }else{
                                    System.out.println("Location: http://" + urlSelect[0] + "\r\n")
                                }
                            }else{
                                indexResponse(ErrorRespMsg.BADSHORTCODE)
                            }
                        }else{
                            indexResponse(ErrorRespMsg.WRONG)
                        }
                    }else{
                        indexResponse()
                    }
                }
            }catch(Exception e){
                log.error("Error: " + e)
                indexResponse(ErrorRespMsg.WRONG)
            }
        }
    }
    static void main(String[] args) {
        InvokerHelper.runScript(Shortener, args)
    }
}
